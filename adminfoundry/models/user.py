from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from adminfoundry.models.base import GlobalModel

if TYPE_CHECKING:
    from adminfoundry.models.tenant_membership import TenantMembership


class User(GlobalModel):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    is_superadmin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    token_version: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    memberships: Mapped[list[TenantMembership]] = relationship(
        "TenantMembership",
        back_populates="user",
        cascade="all, delete-orphan",
    )
