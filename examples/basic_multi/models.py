from sqlalchemy import String, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from adminfoundry.models.base import TimestampedBase


class Project(TimestampedBase):
    __tablename__ = "projects"

    name:      Mapped[str]  = mapped_column(String(255), nullable=False)
    active:    Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    tenant_id: Mapped[str]  = mapped_column(
        String(36), ForeignKey("tenants.id"), nullable=True, index=True
    )
