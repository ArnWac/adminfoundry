from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from adminfoundry.audit import (
    CRUD_CREATE,
    CRUD_DELETE,
    CRUD_UPDATE,
    record_audit_in_session,
    request_audit_kwargs,
)
from adminfoundry.auth.dependencies import get_current_user
from adminfoundry.authz.permissions import permission_key
from adminfoundry.crud.services import (
    create_record,
    delete_record,
    list_records,
    read_record,
    update_record,
)
from adminfoundry.db.dependencies import get_async_session
from adminfoundry.models.user import User
from adminfoundry.registry import ModelAdmin
from adminfoundry.security.validation import (
    InvalidResourceNameError,
    validate_resource_name,
)
from adminfoundry.tenancy.context import TenantAuthContext
from adminfoundry.tenancy.dependencies import require_tenant_auth_context

logger = logging.getLogger(__name__)
router = APIRouter()


def _get_admin_class(request: Request, resource: str) -> type[ModelAdmin]:
    try:
        resource = validate_resource_name(resource)
    except InvalidResourceNameError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource '{resource}' is not registered.",
        ) from None
    admin_class = request.app.state.adminfoundry.registry.get(resource)
    if admin_class is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource '{resource}' is not registered.",
        )
    return admin_class


def _require_resource_permission(
    auth: TenantAuthContext | None,
    resource: str,
    action: str,
) -> None:
    if auth is None:
        return  # root panel (superadmin) or no tenant context
    required = permission_key(resource, action)
    if not auth.has_permission(required):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Missing required permission: {required}",
        )


async def _audit_crud(
    session: AsyncSession,
    request: Request,
    *,
    action: str,
    status_code: int,
    auth: TenantAuthContext | None,
    actor: User,
    resource: str,
    record_id: str | int | None = None,
    changes: dict[str, Any] | None = None,
) -> None:
    """Defense in depth: wrap the in-session audit helper so any failure
    short of an OS-level error is logged and not surfaced as a 500."""
    try:
        kwargs = request_audit_kwargs(request, status_code=status_code)
        if auth is not None:
            kwargs["tenant_id"] = auth.tenant.id
        await record_audit_in_session(
            session,
            action=action,
            actor=actor,
            resource=resource,
            record_id=record_id,
            changes=changes,
            **kwargs,
        )
    except Exception:
        logger.warning(
            "crud audit hook failed for action=%s resource=%s",
            action,
            resource,
            exc_info=True,
        )


@router.get("/{resource}")
async def crud_list(
    resource: str,
    request: Request,
    limit: int = 100,
    offset: int = 0,
    search: str | None = None,
    session: AsyncSession = Depends(get_async_session),
    auth: TenantAuthContext | None = Depends(require_tenant_auth_context),
) -> dict[str, Any]:
    admin_class = _get_admin_class(request, resource)
    _require_resource_permission(auth, admin_class.model_name, "list")
    return await list_records(session, admin_class, limit=limit, offset=offset, search=search)


@router.post("/{resource}", status_code=status.HTTP_201_CREATED)
async def crud_create(
    resource: str,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    auth: TenantAuthContext | None = Depends(require_tenant_auth_context),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    admin_class = _get_admin_class(request, resource)
    _require_resource_permission(auth, admin_class.model_name, "create")
    payload = await request.json()
    result = await create_record(session, admin_class, payload)
    await _audit_crud(
        session,
        request,
        action=CRUD_CREATE,
        status_code=201,
        auth=auth,
        actor=current_user,
        resource=admin_class.model_name,
        record_id=result.get("id"),
        changes=payload,
    )
    return result


@router.get("/{resource}/{record_id}")
async def crud_read(
    resource: str,
    record_id: str,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    auth: TenantAuthContext | None = Depends(require_tenant_auth_context),
) -> dict[str, Any]:
    admin_class = _get_admin_class(request, resource)
    _require_resource_permission(auth, admin_class.model_name, "read")
    return await read_record(session, admin_class, record_id)


@router.patch("/{resource}/{record_id}")
async def crud_update(
    resource: str,
    record_id: str,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    auth: TenantAuthContext | None = Depends(require_tenant_auth_context),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    admin_class = _get_admin_class(request, resource)
    _require_resource_permission(auth, admin_class.model_name, "update")
    payload = await request.json()
    result = await update_record(session, admin_class, record_id, payload)
    await _audit_crud(
        session,
        request,
        action=CRUD_UPDATE,
        status_code=200,
        auth=auth,
        actor=current_user,
        resource=admin_class.model_name,
        record_id=record_id,
        changes=payload,
    )
    return result


@router.delete("/{resource}/{record_id}")
async def crud_delete(
    resource: str,
    record_id: str,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    auth: TenantAuthContext | None = Depends(require_tenant_auth_context),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    admin_class = _get_admin_class(request, resource)
    _require_resource_permission(auth, admin_class.model_name, "delete")
    result = await delete_record(session, admin_class, record_id)
    await _audit_crud(
        session,
        request,
        action=CRUD_DELETE,
        status_code=200,
        auth=auth,
        actor=current_user,
        resource=admin_class.model_name,
        record_id=record_id,
    )
    return result
