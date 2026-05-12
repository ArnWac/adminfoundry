"""Structural protocols for pluggable model support."""
from __future__ import annotations
from typing import Any


def validate_user_model(model_cls: type) -> None:
    """Raise ValueError if model_cls is missing required user fields.

    Required: id, email, is_active, is_superadmin
    """
    required = ("id", "email", "is_active", "is_superadmin")
    try:
        from sqlalchemy import inspect as sa_inspect
        mapper = sa_inspect(model_cls)
        col_names = {c.key for c in mapper.mapper.column_attrs}
    except Exception:
        col_names = set()

    all_attrs = col_names | set(dir(model_cls))
    missing = [f for f in required if f not in all_attrs]
    if missing:
        raise ValueError(
            f"{model_cls.__name__!r} is missing required user model fields: {missing}. "
            f"Required: {list(required)}"
        )
