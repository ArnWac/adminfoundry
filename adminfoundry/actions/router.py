"""Admin actions router.

Exposes ``POST /api/v1/admin/{resource}/_actions/{action}``. The action's
``execute`` method receives the resolved records, the request-scoped session,
and the current user. The session transaction is owned by
``get_async_session`` — actions must flush, not commit.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from adminfoundry.actions import AdminAction
from adminfoundry.audit import (
    ADMIN_ACTION,
    record_audit_in_session,
    request_audit_kwargs,
)
from adminfoundry.auth.dependencies import get_current_user
from adminfoundry.authz.permissions import permission_key
from adminfoundry.crud.query import coerce_primary_key_value, primary_key_column
from adminfoundry.db.dependencies import get_async_session
from adminfoundry.models.user import User
from adminfoundry.registry import ModelAdmin
from adminfoundry.security.validation import (
    InvalidActionNameError,
    InvalidResourceNameError,
    validate_action_name,
    validate_resource_name,
)
from adminfoundry.tenancy.context import TenantAuthContext
from adminfoundry.tenancy.dependencies import require_tenant_auth_context

logger = logging.getLogger(__name__)
router = APIRouter()


class ActionRequest(BaseModel):
    ids: list[Any] = Field(default_factory=list)


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _resolve_admin(request: Request, resource: str) -> type[ModelAdmin]:
    try:
        resource = validate_resource_name(resource)
    except InvalidResourceNameError:
        raise _not_found(f"Resource '{resource}' is not registered.") from None
    admin = request.app.state.adminfoundry.registry.get(resource)
    if admin is None:
        raise _not_found(f"Resource '{resource}' is not registered.")
    return admin


def _resolve_action(admin: ModelAdmin, action_name: str) -> AdminAction:
    try:
        action_name = validate_action_name(action_name)
    except InvalidActionNameError:
        raise _not_found(f"Action '{action_name}' is not declared.") from None
    for candidate in admin.actions:
        if getattr(candidate, "name", None) == action_name:
            return candidate
    raise _not_found(f"Action '{action_name}' is not declared.")


def _require_permission(
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


async def _resolve_records(
    session: AsyncSession,
    admin: ModelAdmin,
    raw_ids: list[Any],
) -> list[Any]:
    if not raw_ids:
        return []
    model = admin.model
    pk_column = primary_key_column(model)
    coerced = [coerce_primary_key_value(model, str(raw)) for raw in raw_ids]
    result = await session.execute(select(model).where(pk_column.in_(coerced)))
    return list(result.scalars().all())


@router.post("/{resource}/_actions/{action}")
async def run_action(
    resource: str,
    action: str,
    payload: ActionRequest,
    request: Request,
    session: AsyncSession = Depends(get_async_session),
    auth: TenantAuthContext | None = Depends(require_tenant_auth_context),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    admin = _resolve_admin(request, resource)
    action_instance = _resolve_action(admin, action)
    _require_permission(auth, admin.model_name, action_instance.name)
    records = await _resolve_records(session, admin, payload.ids)
    result = await action_instance.execute(records, session, current_user)
    if not isinstance(result, dict):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Action did not return a dict result.",
        )
    try:
        await record_audit_in_session(
            session,
            action=ADMIN_ACTION,
            actor=current_user,
            resource=admin.model_name,
            tenant_id=auth.tenant.id if auth is not None else None,
            changes={
                "action": action_instance.name,
                "ids": [str(i) for i in payload.ids],
                "affected": result.get("affected"),
            },
            **request_audit_kwargs(request, status_code=200),
        )
    except Exception:
        logger.warning(
            "admin action audit hook failed for resource=%s action=%s",
            admin.model_name,
            action_instance.name,
            exc_info=True,
        )
    return result
