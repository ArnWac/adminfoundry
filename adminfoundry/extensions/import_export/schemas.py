import uuid
from pydantic import BaseModel


class ImportRowResult(BaseModel):
    row_index: int
    success: bool
    errors: list[str] = []
    data: dict | None = None


class ImportRequest(BaseModel):
    rows: list[dict]
    dry_run: bool = True
    idempotency_key: str | None = None


class ImportResult(BaseModel):
    dry_run: bool
    total: int
    success_count: int
    error_count: int
    rows: list[ImportRowResult]
    job_id: uuid.UUID | None = None


class ExportResult(BaseModel):
    job_id: uuid.UUID
    status: str
    row_count: int | None
    data: list[dict] | None = None


class BulkActionRequest(BaseModel):
    action: str
    object_ids: list[uuid.UUID]
    confirm: bool = False
    idempotency_key: str | None = None
