# ADR-0002 — Privacy as a core module, not an extension

**Status:** Accepted

## Context

asterion has an extension SPI for optional, third-party-style building blocks
(see [extensions.md](../extensions.md)). When the data-protection features (PII
classification, anonymisation, retention, audit redaction) were planned, the
question was whether they should ship as an extension or in core.

The extension SPI is explicitly for *optional* capabilities a deployment can
take or leave. But privacy features reach into **core models** (`User`,
`AuditLog`, `TenantAuditLog`, `Tenant`) and **core flows** (the audit writer, the
tenant lifecycle). Anonymisation rewrites the `users` row and audit actor fields;
audit redaction sits on the write path of every audit row; retention iterates
tenant schemas. These are not opt-in add-ons — they are how the framework
behaves with personal data.

## Decision

Ship privacy as a **core module**, `asterion/privacy/`, not an extension. The
default behaviour is privacy-preserving out of the box (audit PII is redacted and
behavioural values suppressed by default; the secure defaults apply before any
wiring runs).

Extensibility is preserved the way the protected-field machinery already does it:
the **PII classification** is a contributable registry
([`PIIFieldRegistry`](../../asterion/privacy/classification.py)), so apps and
extensions register their own classified fields before `create_admin` freezes it.
External delivery (subject export, etc.) reuses the existing
`StorageBackend` / `Notifier` Protocols rather than inventing a new surface.

## Consequences

- **Positive:** data-minimising behaviour is the default, not an install step a
  deployment can forget; privacy code can depend directly on core models and the
  audit writer; one obvious home (`asterion/privacy/`) for classification,
  anonymiser, redaction, retention.
- **Negative:** core carries more surface; a deployment that wanted *no* privacy
  logic still gets it (mitigated: it's cheap and configurable — e.g.
  `audit_pii_mode="keep"`).
- **Extensibility kept:** the classification registry is the contribution point,
  mirroring [`ProtectedFieldRegistry`](../../asterion/security/protected_fields.py).

See [PRIVACY.md](../PRIVACY.md) and the roadmap's G-block rationale in
[roadmap.md](../roadmap.md).
