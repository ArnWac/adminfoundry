"""Contract building service: introspects ModelAdmin and SQLAlchemy models."""

from __future__ import annotations

import sqlalchemy.types as sqltypes
from pydantic import BaseModel
from sqlalchemy import inspect as sa_inspect

from adminfoundry.registry.admin import ModelAdmin

CONTRACT_VERSION = "1"

CRUD_ACTIONS: tuple[str, ...] = ("list", "read", "create", "update", "delete")


class FieldMeta(BaseModel):
    name: str
    type: str
    primary_key: bool = False
    read_only: bool = False
    hidden: bool = False
    nullable: bool = False
    calculated: bool = False


class AdminActionMeta(BaseModel):
    name: str
    label: str


class ModelContractMeta(BaseModel):
    contract_version: str
    resource: str
    label: str
    label_plural: str
    description: str | None = None
    fields: list[FieldMeta]
    crud_actions: list[str]
    admin_actions: list[AdminActionMeta]
    list_display: list[str]
    search_fields: list[str]
    ordering: list[str]


def _field_type(sa_type) -> str:
    type_name = type(sa_type).__name__.lower()
    if "uuid" in type_name or "guid" in type_name:
        return "uuid"
    if isinstance(sa_type, sqltypes.Boolean):
        return "boolean"
    if isinstance(sa_type, (sqltypes.BigInteger, sqltypes.SmallInteger, sqltypes.Integer)):
        return "integer"
    if isinstance(sa_type, (sqltypes.Float, sqltypes.Numeric)):
        return "float"
    if isinstance(sa_type, sqltypes.DateTime):
        return "datetime"
    return "string"


def build_field_metadata(model_admin: ModelAdmin) -> list[FieldMeta]:
    mapper = sa_inspect(model_admin.model)
    protected = model_admin.all_protected
    readonly_set = set(model_admin.readonly_fields)

    fields: list[FieldMeta] = []

    for col in mapper.columns:
        if col.name in protected:
            continue
        is_pk = bool(col.primary_key)
        fields.append(
            FieldMeta(
                name=col.name,
                type=_field_type(col.type),
                primary_key=is_pk,
                read_only=is_pk or col.name in readonly_set,
                hidden=False,
                nullable=bool(col.nullable),
                calculated=False,
            )
        )

    for fname in model_admin.calculated_fields:
        fields.append(
            FieldMeta(
                name=fname,
                type="string",
                primary_key=False,
                read_only=True,
                hidden=False,
                nullable=True,
                calculated=True,
            )
        )

    return fields


def _admin_action_meta(action) -> AdminActionMeta:
    name = getattr(action, "name", None) or getattr(action, "__name__", "unknown")
    label = getattr(action, "label", None) or name.replace("_", " ").title()
    return AdminActionMeta(name=name, label=label)


def build_model_contract(model_admin: ModelAdmin) -> ModelContractMeta:
    return ModelContractMeta(
        contract_version=CONTRACT_VERSION,
        resource=model_admin.model_name,
        label=model_admin.display_label,
        label_plural=model_admin.display_label_plural,
        description=model_admin.description,
        fields=build_field_metadata(model_admin),
        crud_actions=list(CRUD_ACTIONS),
        admin_actions=[_admin_action_meta(a) for a in model_admin.actions],
        list_display=list(model_admin.list_display),
        search_fields=list(model_admin.search_fields),
        ordering=list(model_admin.ordering),
    )
