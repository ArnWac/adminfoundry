"""
Pluggable authentication provider.

Override AuthProvider to integrate existing auth while keeping the admin UI:

    from adminfoundry.auth_provider import AuthProvider

    class MyAuthProvider(AuthProvider):
        async def authenticate(self, request, token, db):
            user = await my_app.get_user_from_token(token)
            if user is None:
                raise HTTPException(status_code=401, detail="Invalid token")
            return user

        def is_superadmin(self, user) -> bool:
            return user.is_staff

        def get_role_names(self, user) -> list[str]:
            return [g.name for g in user.groups]
"""
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from adminfoundry.auth import decode_token
from adminfoundry.token_blacklist import is_blacklisted
from adminfoundry.models.user import User


class AuthProvider:
    """Default JWT-based auth provider. Subclass to replace with custom logic.

    user_model: override to use a custom SQLAlchemy user model instead of the
    built-in User. The model must satisfy validate_user_model() requirements.
    Set via CoreAdminConfig(user_model=MyUser) — do not import User at class level.
    """

    user_model: type | None = None

    def _get_user_model(self) -> type:
        if self.user_model is not None:
            return self.user_model
        return User

    async def authenticate(self, request: Request, token: str, db: AsyncSession) -> Any:
        """Return the authenticated user or raise HTTP 401."""
        payload = decode_token(token, expected_type="access")
        if payload is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        jti = payload.get("jti", "")
        if await is_blacklisted(jti, db):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")

        request.state.token_payload = payload

        UserModel = self._get_user_model()
        user_id = payload.get("sub")
        result = await db.execute(select(UserModel).where(UserModel.id == user_id))
        user = result.scalar_one_or_none()

        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        if payload.get("tkv", 0) != user.token_version:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been invalidated — please log in again",
            )

        request.state.audit_user_id = str(user.id)
        return user

    def is_superadmin(self, user: Any) -> bool:
        return bool(getattr(user, "is_superadmin", False))

    def get_role_names(self, user: Any) -> list[str]:
        return [r.name for r in getattr(user, "roles", [])]
