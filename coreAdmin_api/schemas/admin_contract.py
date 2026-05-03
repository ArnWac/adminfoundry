from __future__ import annotations
from pydantic import BaseModel


class RelationMeta(BaseModel):
    """Minimal relation metadata for FK fields — no backend internals."""
    target_table: str           # e.g. "tenants"
    lookup_url: str | None = None   # e.g. "/api/v1/admin/tenants/lookup"
    label_field: str | None = None  # field used as display label in selection widgets


class FieldMeta(BaseModel):
    name: str
    label: str          # human-readable, title-cased
    field_type: str     # "string" | "integer" | "float" | "boolean" | "datetime" | "uuid"
    required: bool      # not nullable and no default — relevant for create forms
    nullable: bool
    has_default: bool
    readonly: bool      # mutation via CRUD rejected with 422
    in_list: bool       # shown in list_display
    searchable: bool    # in search_fields
    filterable: bool    # in filter_fields
    sortable: bool      # column supports order_by
    widget: str         # renderer hint: "text"|"number"|"checkbox"|"datetime"|"uuid-display"|"select-relation"
    relation: RelationMeta | None = None
    # Phase 10: effective policy for the requesting user (defaults True = no restriction)
    policy_visible: bool = True
    policy_editable: bool = True


class ActionMeta(BaseModel):
    name: str
    label: str
    danger: bool = False
    confirm: bool = False   # requires explicit confirmation before execution
    bulk: bool = False      # applicable to multiple selected records
    single: bool = True     # applicable to a single record


class ModelContractMeta(BaseModel):
    contract_version: str       # e.g. "1" — bump major on breaking changes
    model: str
    label: str
    label_plural: str
    description: str | None
    tenant_scoped: bool
    fields: list[FieldMeta]
    list_fields: list[str]
    search_fields: list[str]
    filter_fields: list[str]
    ordering: list[str]
    readonly_fields: list[str]
    actions: list[ActionMeta]
