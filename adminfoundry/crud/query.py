from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import String, cast, func, inspect, or_, select
from sqlalchemy.orm import ColumnProperty
from sqlalchemy.sql import Select

from adminfoundry.registry import ModelAdmin
from adminfoundry.security.validation import (
    DEFAULT_PAGE_LIMIT as DEFAULT_LIMIT,
)
from adminfoundry.security.validation import (
    validate_limit_offset,
)


def normalize_limit_offset(
    *,
    limit: int = DEFAULT_LIMIT,
    offset: int = 0,
) -> tuple[int, int]:
    return validate_limit_offset(limit=limit, offset=offset)


def primary_key_column(model: type[Any]):
    mapper = inspect(model)
    primary_key = mapper.primary_key

    if len(primary_key) != 1:
        raise RuntimeError(f"CRUD only supports models with exactly one primary key: {model!r}")

    return primary_key[0]


def coerce_primary_key_value(model: type[Any], value: str) -> Any:
    pk_column = primary_key_column(model)

    try:
        python_type = pk_column.type.python_type
    except NotImplementedError:
        python_type = str

    if python_type is int:
        try:
            return int(value)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Invalid integer primary key.",
            ) from exc

    if python_type is uuid.UUID:
        try:
            return uuid.UUID(value)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Invalid UUID primary key.",
            ) from exc

    return value


def model_column_names(model: type[Any]) -> set[str]:
    mapper = inspect(model)

    names: set[str] = set()

    for attr in mapper.attrs:
        if isinstance(attr, ColumnProperty):
            names.add(attr.key)

    return names


def get_model_column(model: type[Any], field_name: str):
    columns = inspect(model).columns

    if field_name not in columns:
        raise ValueError(f"Unknown column for model {model!r}: {field_name}")

    return columns[field_name]


def apply_ordering(
    stmt: Select,
    admin_class: type[ModelAdmin],
) -> Select:
    model = admin_class.model

    ordering = tuple(getattr(admin_class, "ordering", ()) or ())

    if not ordering:
        return stmt.order_by(primary_key_column(model).asc())

    known_columns = model_column_names(model)

    order_clauses = []

    for item in ordering:
        descending = item.startswith("-")
        field_name = item[1:] if descending else item

        if field_name not in known_columns:
            raise RuntimeError(
                f"{admin_class.__name__}.ordering contains unknown field: {field_name}"
            )

        column = get_model_column(model, field_name)
        order_clauses.append(column.desc() if descending else column.asc())

    return stmt.order_by(*order_clauses)


def apply_search(
    stmt: Select,
    admin_class: type[ModelAdmin],
    search: str | None,
) -> Select:
    if search is None or not search.strip():
        return stmt

    model = admin_class.model
    search_fields = tuple(getattr(admin_class, "search_fields", ()) or ())

    if not search_fields:
        return stmt

    known_columns = model_column_names(model)
    search_value = f"%{search.strip()}%"

    clauses = []

    for field_name in search_fields:
        if field_name not in known_columns:
            raise RuntimeError(
                f"{admin_class.__name__}.search_fields contains unknown field: {field_name}"
            )

        column = get_model_column(model, field_name)
        clauses.append(cast(column, String).ilike(search_value))

    if not clauses:
        return stmt

    return stmt.where(or_(*clauses))


def count_statement_for(stmt: Select) -> Select:
    return select(func.count()).select_from(stmt.order_by(None).limit(None).offset(None).subquery())
