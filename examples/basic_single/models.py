from sqlalchemy import String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from adminfoundry.models.base import TimestampedBase


class Post(TimestampedBase):
    __tablename__ = "posts"

    title:     Mapped[str]  = mapped_column(String(255), nullable=False)
    content:   Mapped[str]  = mapped_column(Text,        nullable=False, default="")
    author:    Mapped[str]  = mapped_column(String(255), nullable=False, default="")
    published: Mapped[bool] = mapped_column(Boolean,     nullable=False, default=False)
