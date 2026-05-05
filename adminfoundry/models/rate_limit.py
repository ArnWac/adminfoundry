from sqlalchemy import String, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column
from adminfoundry.models.base import Base


class RateLimitRequest(Base):
    __tablename__ = "rate_limit_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    ts: Mapped[float] = mapped_column(Float, nullable=False)
