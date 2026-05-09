from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from adminfoundry.models.base import TimestampedBase


class Tenant(TimestampedBase):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(63), unique=True, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Locale — serve as the middle tier between app defaults and user preferences.
    # All nullable: None means "inherit from app default".
    # timezone: IANA name, e.g. "Europe/Berlin", "America/New_York", "UTC"
    timezone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # language: BCP 47 tag, e.g. "de", "en", "fr", "pt-BR"
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # date_format: "locale" | "iso" | "eu" | "us" | "custom"
    date_format: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # date_pattern: strftime pattern used when date_format = "custom"
    date_pattern: Mapped[str | None] = mapped_column(String(64), nullable=True)

    @property
    def schema_name(self) -> str:
        return f"tenant_{self.slug}"
