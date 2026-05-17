from sqlalchemy import String, Index
from sqlalchemy.orm import Mapped, mapped_column

from adminfoundry.models.base import TimestampedBase


class PermissionCatalog(TimestampedBase):
    """Global registry of permission keys known to the framework.

    Tenant-local role_permissions reference these keys. The catalog is owned
    by the framework and seeded from registered ModelAdmin names; tenants
    cannot add or remove keys.
    """

    __tablename__ = "permission_catalog"
    __table_args__ = (Index("ix_permission_catalog_key", "key", unique=True),)

    key: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    source: Mapped[str | None] = mapped_column(String(200), nullable=True)
