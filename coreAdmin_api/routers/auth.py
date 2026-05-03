from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from coreAdmin_api.database import get_db
from coreAdmin_api.models.user import User
from coreAdmin_api.schemas.auth import LoginRequest, TokenResponse, RefreshRequest
from coreAdmin_api.schemas.user import UserPublic
from coreAdmin_api.auth import verify_password, create_access_token, create_refresh_token, decode_token
from coreAdmin_api.dependencies import get_current_user
from coreAdmin_api.token_blacklist import blacklist_token

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Account inactive")

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = decode_token(body.refresh_token, expected_type="refresh")
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    # Impersonation tokens carry renewable=False; explicitly block any refresh token marked non-renewable
    if payload.get("renewable") is False:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is not renewable"
        )

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    _: User = Depends(get_current_user),
):
    """Revoke the current access token by blacklisting its JTI."""
    payload = getattr(request.state, "token_payload", {})
    jti = payload.get("jti", "")
    exp = payload.get("exp", 0)
    if jti:
        blacklist_token(jti, exp)


@router.get("/me", response_model=UserPublic)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
