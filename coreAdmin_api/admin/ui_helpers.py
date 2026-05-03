"""Lightweight helpers for the built-in admin UI renderer."""
from __future__ import annotations

from coreAdmin_api.admin.registry import Registry


def get_model_names(registry: Registry) -> list[str]:
    return registry.model_names()


def ui_field_input_type(field_type: str) -> str:
    """Map contract field_type to an HTML input type hint."""
    return {
        "boolean": "checkbox",
        "integer": "number",
        "float": "number",
        "datetime": "datetime-local",
        "uuid": "text",
    }.get(field_type, "text")
