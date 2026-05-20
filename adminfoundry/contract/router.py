"""Admin contract API.

Exposes registered ModelAdmin metadata so the UI / API clients can render
forms, list columns, and validate inputs without hitting CRUD endpoints.

Hidden fields, per-admin protected_fields, and globally protected fields are
never emitted. Resource names are validated through the security validator so
malformed paths fall through to 404 rather than reaching the registry.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from adminfoundry.auth.dependencies import get_current_user
from adminfoundry.contract.service import (
    CONTRACT_VERSION,
    ModelContractMeta,
    build_model_contract,
)
from adminfoundry.models.user import User
from adminfoundry.security.validation import (
    InvalidResourceNameError,
    validate_resource_name,
)

router = APIRouter()


@router.get("/_contract")
async def get_full_contract(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> dict:
    runtime = request.app.state.adminfoundry
    return {
        "contract_version": CONTRACT_VERSION,
        "models": [build_model_contract(admin).model_dump() for admin in runtime.registry.all()],
    }


@router.get("/_contract/{resource}", response_model=ModelContractMeta)
async def get_model_contract(
    resource: str,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> ModelContractMeta:
    try:
        resource = validate_resource_name(resource)
    except InvalidResourceNameError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource '{resource}' is not registered.",
        ) from None
    runtime = request.app.state.adminfoundry
    admin = runtime.registry.get(resource)
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource '{resource}' is not registered.",
        )
    return build_model_contract(admin)
