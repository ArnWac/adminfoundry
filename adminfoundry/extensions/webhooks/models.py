import uuid
from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from adminfoundry.models.base import GUID, TimestampedBase


class WebhookSubscription(TimestampedBase):
    """An HTTP endpoint registered to receive admin signal events."""

    __tablename__ = "webhook_subscriptions"

    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    events: Mapped[str] = mapped_column(
        Text, nullable=False,
        doc="JSON array of event names, e.g. '[\"post_create\", \"post_delete\"]'",
    )
    secret: Mapped[str | None] = mapped_column(String(512), nullable=True)
    model_filter: Mapped[str | None] = mapped_column(
        Text, nullable=True,
        doc="JSON array of model names to filter; null = all models",
    )
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class WebhookDelivery(TimestampedBase):
    """Delivery attempt record for a webhook subscription."""

    __tablename__ = "webhook_deliveries"

    subscription_id: Mapped[uuid.UUID] = mapped_column(GUID, nullable=False, index=True)
    event: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32), default="pending", nullable=False,
        doc="pending | delivered | failed",
    )
    response_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
