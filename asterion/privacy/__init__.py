"""Core privacy / data-protection module (roadmap block G1-G8).

Privacy lives in **core**, not in an extension: anonymisation, retention and
PII-aware redaction reach into core models (``User``, ``AuditLog``,
``TenantAuditLog``, ``Tenant``) and core flows (the audit writer, the tenant
lifecycle), so it is core behaviour rather than an optional plugin. Extensibility
is preserved the same way the protected-field machinery does it: PII
classification is a contributable registry (see :mod:`.classification`).

This package ships the **G1 foundation** (PII classification registry), the
**G2 anonymiser** (:mod:`.anonymizer`), **G3 retention** (:mod:`.retention`),
**G7 audit redaction** (:mod:`.redaction`) and **G8 subject export + DSAR log**
(:mod:`.export`). Tenant offboarding (G6) lives in :mod:`asterion.tenancy`.
"""

from __future__ import annotations

from asterion.privacy.anonymizer import (
    anonymize_audit_actor,
    anonymize_user,
    anonymized_email,
)
from asterion.privacy.classification import (
    DEFAULT_PII_FIELDS,
    PIICategory,
    PIIFieldRegistry,
    get_pii_registry,
    reset_for_tests,
)
from asterion.privacy.export import (
    SubjectNotFoundError,
    SubjectRequestStatus,
    SubjectRequestType,
    export_subject,
    list_subject_requests,
    record_subject_request,
)
from asterion.privacy.redaction import (
    AuditPIIMode,
    get_default_audit_pii_mode,
    get_default_behavioral_detail,
    redact_pii,
    set_default_audit_pii_mode,
    set_default_behavioral_detail,
    suppress_behavioral,
)
from asterion.privacy.retention import (
    apply_retention,
    prune_public_audit,
    prune_tenant_audit,
    retention_cutoff,
)

__all__ = [
    "DEFAULT_PII_FIELDS",
    "AuditPIIMode",
    "PIICategory",
    "PIIFieldRegistry",
    "SubjectNotFoundError",
    "SubjectRequestStatus",
    "SubjectRequestType",
    "anonymize_audit_actor",
    "anonymize_user",
    "anonymized_email",
    "apply_retention",
    "export_subject",
    "get_default_audit_pii_mode",
    "get_default_behavioral_detail",
    "get_pii_registry",
    "list_subject_requests",
    "prune_public_audit",
    "prune_tenant_audit",
    "record_subject_request",
    "redact_pii",
    "reset_for_tests",
    "retention_cutoff",
    "set_default_audit_pii_mode",
    "set_default_behavioral_detail",
    "suppress_behavioral",
]
