"""PII-aware redaction of audit ``changes`` (roadmap G7 + G5).

The audit writer already strips *secret* keys (passwords, tokens) via
:func:`asterion.security.sanitize.sanitize_payload`. This layer adds two
data-protection passes on top, both driven by the G1
:class:`~asterion.privacy.classification.PIIFieldRegistry`:

* **G7 — PII masking** (:func:`redact_pii`): values of fields classified as
  ``IDENTITY`` / ``CONTACT`` / ``SENSITIVE`` are masked per ``audit_pii_mode``,
  so an audit leak (or over-broad reader) never sees the value itself. The row
  still records *that* the field changed, just not *to what* (Art. 5).
* **G5 — behavioural-detail policy** (:func:`suppress_behavioral`): values of
  ``BEHAVIORAL``-classified fields (employee activity — punches, edits) are
  suppressed by default and only kept when ``audit_behavioral_detail`` is on.
  This prevents the audit trail from silently becoming a continuous
  value-level monitoring record of employees (§26 BDSG / Art. 88).

The two passes are disjoint by category — ``BEHAVIORAL`` is handled by G5, never
by G7 — so the behavioural opt-in is meaningful. Both defaults are process-wide,
set once by ``create_admin``; the secure defaults (``"redact"`` + suppress) apply
even before any wiring runs.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any, Literal

from asterion.privacy.classification import (
    PIICategory,
    PIIFieldRegistry,
    get_pii_registry,
)

#: ``redact`` masks the value; ``hash`` replaces it with a short SHA-256 tag
#: (equal values stay correlatable across rows without revealing them);
#: ``keep`` opts out (raw value retained).
AuditPIIMode = Literal["redact", "hash", "keep"]

REDACTED_PII = "***PII***"
SUPPRESSED_BEHAVIORAL = "***BEHAVIORAL***"

#: Categories masked by the G7 PII pass. ``BEHAVIORAL`` is deliberately excluded
#: — it is governed by the G5 behavioural-detail opt-in instead.
_REDACTABLE_CATEGORIES = frozenset(
    {PIICategory.IDENTITY, PIICategory.CONTACT, PIICategory.SENSITIVE}
)

_default_mode: AuditPIIMode = "redact"
_default_behavioral_detail: bool = False


def set_default_audit_pii_mode(mode: AuditPIIMode) -> None:
    """Set the process-wide default mode (called once from ``create_admin``)."""
    global _default_mode
    _default_mode = mode


def get_default_audit_pii_mode() -> AuditPIIMode:
    return _default_mode


def set_default_behavioral_detail(enabled: bool) -> None:
    """Set the process-wide behavioural-detail opt-in (from ``create_admin``)."""
    global _default_behavioral_detail
    _default_behavioral_detail = enabled


def get_default_behavioral_detail() -> bool:
    return _default_behavioral_detail


def _mask(value: Any, mode: AuditPIIMode) -> Any:
    if mode == "hash":
        digest = hashlib.sha256(repr(value).encode("utf-8")).hexdigest()
        return f"pii:sha256:{digest[:16]}"
    return REDACTED_PII


def redact_pii(
    changes: Any,
    *,
    mode: AuditPIIMode | None = None,
    registry: PIIFieldRegistry | None = None,
) -> Any:
    """Return a copy of ``changes`` with PII-classified values masked per ``mode``.

    Masks ``IDENTITY`` / ``CONTACT`` / ``SENSITIVE`` fields only — ``BEHAVIORAL``
    is left untouched here (see :func:`suppress_behavioral`). Audit ``changes``
    are a flat ``{field: new_value}`` mapping (the write payload), so only
    top-level keys are inspected. Non-mapping input and ``None`` values pass
    through unchanged; ``mode="keep"`` is a no-op.
    """
    resolved = mode or _default_mode
    if not isinstance(changes, Mapping):
        return changes
    if resolved == "keep":
        return dict(changes)
    reg = registry or get_pii_registry()
    out: dict[Any, Any] = {}
    for key, value in changes.items():
        if value is not None and reg.category_of(key) in _REDACTABLE_CATEGORIES:
            out[key] = _mask(value, resolved)
        else:
            out[key] = value
    return out


def suppress_behavioral(
    changes: Any,
    *,
    detail: bool | None = None,
    registry: PIIFieldRegistry | None = None,
) -> Any:
    """Suppress the *values* of ``BEHAVIORAL``-classified fields (G5).

    When ``detail`` is False (the default minimal level), each ``BEHAVIORAL``
    field's value is replaced with :data:`SUPPRESSED_BEHAVIORAL` — the row keeps
    *that* the field changed but not the value, so the audit trail can't become a
    continuous behavioural-monitoring record without an explicit opt-in. When
    ``detail`` is True (``audit_behavioral_detail`` config), values are kept.
    """
    resolved = _default_behavioral_detail if detail is None else detail
    if resolved or not isinstance(changes, Mapping):
        return changes if not isinstance(changes, Mapping) else dict(changes)
    reg = registry or get_pii_registry()
    out: dict[Any, Any] = {}
    for key, value in changes.items():
        if value is not None and reg.category_of(key) is PIICategory.BEHAVIORAL:
            out[key] = SUPPRESSED_BEHAVIORAL
        else:
            out[key] = value
    return out
