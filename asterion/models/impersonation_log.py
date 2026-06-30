from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from asterion.models.base import GUID, GlobalModel


class ImpersonationLog(GlobalModel):
    __tablename__ = "impersonation_logs"

    superadmin_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        nullable=False,
        index=True,
    )

    target_user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        nullable=False,
        index=True,
    )

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID(),
        nullable=True,
        index=True,
    )

    jti: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )

    #: Documented purpose for the impersonation (G9). Nullable at the column
    #: level so historical rows and ``impersonation_require_reason=False``
    #: deployments stay valid; the route enforces presence when the config
    #: flag is on. Mirrored into the audit ``changes`` for the governance trail.
    reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
