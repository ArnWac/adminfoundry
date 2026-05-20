from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adminfoundry.crud.payload import clean_write_payload
from adminfoundry.crud.query import (
    apply_ordering,
    apply_search,
    coerce_primary_key_value,
    count_statement_for,
    normalize_limit_offset,
    primary_key_column,
)
from adminfoundry.crud.types import PageResult
from adminfoundry.registry import ModelAdmin
from adminfoundry.schemas.builder import build_model_schema
from adminfoundry.schemas.serialization.serializer import serialize_record, serialize_records


async def get_record_or_404(
    session: AsyncSession,
    admin_class: type[ModelAdmin],
    record_id: str,
) -> Any:
    model = admin_class.model
    pk_column = primary_key_column(model)
    pk_value = coerce_primary_key_value(model, record_id)

    result = await session.execute(select(model).where(pk_column == pk_value))
    record = result.scalar_one_or_none()

    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record not found.",
        )

    return record


async def list_records(
    session: AsyncSession,
    admin_class: type[ModelAdmin],
    *,
    limit: int = 100,
    offset: int = 0,
    search: str | None = None,
) -> dict[str, Any]:
    model = admin_class.model

    normalized_limit, normalized_offset = normalize_limit_offset(
        limit=limit,
        offset=offset,
    )

    base_stmt = select(model)
    base_stmt = apply_search(base_stmt, admin_class, search)

    total = (await session.execute(count_statement_for(base_stmt))).scalar_one()

    list_stmt = apply_ordering(base_stmt, admin_class)
    list_stmt = list_stmt.limit(normalized_limit).offset(normalized_offset)

    result = await session.execute(list_stmt)
    records = result.scalars().all()

    return PageResult(
        items=serialize_records(records, admin_class),
        total=total,
        limit=normalized_limit,
        offset=normalized_offset,
    ).to_dict()


async def read_record(
    session: AsyncSession,
    admin_class: type[ModelAdmin],
    record_id: str,
) -> dict[str, Any]:
    record = await get_record_or_404(session, admin_class, record_id)
    return serialize_record(record, admin_class)


async def create_record(
    session: AsyncSession,
    admin_class: type[ModelAdmin],
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    model = admin_class.model
    schema = build_model_schema(admin_class)

    cleaned = clean_write_payload(
        payload,
        schema,
        partial=False,
    )

    record = model(**cleaned)

    session.add(record)
    await session.flush()
    await session.refresh(record)

    return serialize_record(record, admin_class, schema=schema)


async def update_record(
    session: AsyncSession,
    admin_class: type[ModelAdmin],
    record_id: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    schema = build_model_schema(admin_class)

    cleaned = clean_write_payload(
        payload,
        schema,
        partial=True,
    )

    record = await get_record_or_404(session, admin_class, record_id)

    for field_name, value in cleaned.items():
        setattr(record, field_name, value)

    await session.flush()
    await session.refresh(record)

    return serialize_record(record, admin_class, schema=schema)


async def delete_record(
    session: AsyncSession,
    admin_class: type[ModelAdmin],
    record_id: str,
) -> dict[str, Any]:
    record = await get_record_or_404(session, admin_class, record_id)

    if getattr(record, "is_system", False):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="System records cannot be deleted.",
        )

    await session.delete(record)
    await session.flush()

    return {"deleted": True}
