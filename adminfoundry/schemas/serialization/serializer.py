from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from adminfoundry.registry.admin import ModelAdmin


def _serialize_value(value: Any) -> Any:
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _calculated_value(fn, obj) -> Any:
    try:
        return _serialize_value(fn(obj))
    except Exception:
        return None


class Serializer:
    def serialize(self, obj: object, model_admin: ModelAdmin) -> dict:
        excluded = model_admin.all_protected
        result: dict = {}

        for col in obj.__table__.columns:  # type: ignore[attr-defined]
            if col.name in excluded:
                continue
            result[col.name] = _serialize_value(getattr(obj, col.name))

        for fname, fn in model_admin.calculated_fields.items():
            result[fname] = _calculated_value(fn, obj)

        return result

    def serialize_many(self, objs: list, model_admin: ModelAdmin) -> list[dict]:
        return [self.serialize(obj, model_admin) for obj in objs]


serializer = Serializer()


def serialize_record(obj, model_admin: ModelAdmin, schema=None) -> dict:
    return serializer.serialize(obj, model_admin)


def serialize_records(objs: list, model_admin: ModelAdmin) -> list[dict]:
    return serializer.serialize_many(objs, model_admin)
