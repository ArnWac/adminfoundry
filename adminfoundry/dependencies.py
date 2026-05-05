from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from adminfoundry.auth_provider import AuthProvider
from adminfoundry.database import get_db

bearer_scheme = HTTPBearer()

_default_provider = AuthProvider()


def _get_provider(request: Request) -> AuthProvider:
    return getattr(request.app.state, "auth_provider", _default_provider)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Any:
    provider = _get_provider(request)
    return await provider.authenticate(request, credentials.credentials, db)


async def require_superadmin(
    request: Request,
    current_user: Any = Depends(get_current_user),
) -> Any:
    provider = _get_provider(request)
    if not provider.is_superadmin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Superadmin required")
    payload = getattr(request.state, "token_payload", {})
    if payload.get("impersonated_by"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Impersonation tokens cannot access superadmin routes",
        )
    return current_user


def require_role(role_name: str):
    async def _check(request: Request, current_user: Any = Depends(get_current_user)) -> Any:
        provider = _get_provider(request)
        if not provider.is_superadmin(current_user) and role_name not in provider.get_role_names(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role_name}' required",
            )
        return current_user

    return _check
