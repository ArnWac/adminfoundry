import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator
from adminfoundry.schemas.role import RolePublic


def _validate_password(v: str | None) -> str | None:
    if v is None:
        return v
    from adminfoundry.settings import settings
    if len(v) < settings.PASSWORD_MIN_LENGTH:
        raise ValueError(f"Password must be at least {settings.PASSWORD_MIN_LENGTH} characters")
    return v


class AuditLogExport(BaseModel):
    created_at: datetime
    action: str | None
    method: str
    path: str
    ip_address: str | None = None

    model_config = {"from_attributes": True}


class UserExportResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None
    created_at: datetime
    roles: list[str]
    audit_log: list[AuditLogExport]
    exported_at: datetime


class UserPublic(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str | None
    is_active: bool
    is_superadmin: bool
    created_at: datetime
    updated_at: datetime
    roles: list[RolePublic] = []

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None
    is_superadmin: bool = False

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        return _validate_password(v)


class UserUpdate(BaseModel):
    full_name: str | None = None
    is_active: bool | None = None
    is_superadmin: bool | None = None


class ProfileUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None
    current_password: str | None = None
    new_password: str | None = None

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str | None) -> str | None:
        return _validate_password(v)


class SelfEraseRequest(BaseModel):
    password: str
