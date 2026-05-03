import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class AuditLogPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    method: str
    path: str
    status_code: int
    user_id: uuid.UUID | None
    tenant_id: uuid.UUID | None
    action: str | None
    object_id: str | None


class ImpersonateRequest(BaseModel):
    target_user_id: uuid.UUID


class ImpersonateResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    impersonation_log_id: uuid.UUID


class RevokeImpersonationRequest(BaseModel):
    jti: str


class BreakGlassRequest(BaseModel):
    reason: str = Field(..., min_length=10, description="Must be at least 10 characters")
    changes: dict[str, Any]


class BreakGlassResponse(BaseModel):
    updated: dict[str, Any]
    audit_ids: list[uuid.UUID]
