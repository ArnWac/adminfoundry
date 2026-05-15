import uuid
from datetime import datetime
from pydantic import BaseModel

# Import/export and bulk-action schemas live in the import_export extension.
# These re-exports keep existing callers working during migration.
from adminfoundry.extensions.import_export.schemas import (  # noqa: F401
    BulkActionRequest,
    ExportResult,
    ImportRequest,
    ImportResult,
    ImportRowResult,
)


class JobRead(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    status: str
    job_type: str
    model_name: str | None
    action_name: str | None
    initiator_id: uuid.UUID
    tenant_id: uuid.UUID | None
    progress: int | None
    result_summary: str | None
    failure_summary: str | None
