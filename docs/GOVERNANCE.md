# Governance

How asterion is governed as a project and how a deployment governs access,
change, and accountability. Pairs with [THREAT_MODEL.md](THREAT_MODEL.md),
[permission-matrix.md](permission-matrix.md),
[shared-responsibility.md](shared-responsibility.md) and the
[ADRs](adr/README.md).

## Decision record

Significant, hard-to-reverse architectural decisions are captured as
[Architecture Decision Records](adr/README.md). Add an ADR before changing a
load-bearing invariant (tenant isolation, the privacy module's location, the
token model). The first three:

- [ADR-0001 — Schema-per-tenant instead of RLS](adr/0001-schema-per-tenant.md)
- [ADR-0002 — Privacy as a core module, not an extension](adr/0002-privacy-as-core-module.md)
- [ADR-0003 — Bearer tokens instead of cookie sessions](adr/0003-bearer-token-not-cookie.md)

## Access governance

| Scope | Who | Gated by |
|---|---|---|
| Global / root (all users, tenants, audit, impersonation) | Superadmin only | `User.is_superadmin`; impersonation tokens are rejected at root routes |
| Single-tenant / no-tenant admin surface | Superadmin by default | `single_tenant_require_superadmin` (default True) |
| Tenant admin surface | Tenant role holders | Tenant RBAC permission keys (`admin.<resource>.<action>`) |

Tenant roles and their default grants are in
[permission-matrix.md](permission-matrix.md). Field-level access is constrained
by `protected_fields` + per-row policies, which can only **tighten** access
(`FieldPermission.strictest`) — see [security.md](security.md#field-protection).

### Privileged-access trail

- **Impersonation** (superadmin acting as a user) requires a documented `reason`
  by default (`impersonation_require_reason`, G9) and writes an
  `ImpersonationLog` + audit row. Review these regularly.
- A **global "Support" role** (least-privilege, non-superadmin cross-tenant
  read) is designed but not yet built (roadmap G14); today cross-tenant access
  is all-or-nothing via `is_superadmin`.

## Change governance

- **Versioning / stability:** `0.x` may make breaking API/contract changes,
  called out in [CHANGELOG.md](../CHANGELOG.md). The public API is
  `asterion.__all__` + the provider Protocols (pinned by `tests/public_api/`);
  the JSON contract is `ModelContractMeta`, with breaking shape changes bumping
  `CONTRACT_VERSION`. Full policy in [roadmap.md](roadmap.md).
- **Release flow & version locations** are documented in
  [CLAUDE.md](../CLAUDE.md) (version lives in `pyproject.toml` **and**
  `asterion/__init__.py`).
- **Tests gate behaviour.** A roadmap item is "done" only when a test locks the
  promise — isolation guarantees require a real-PostgreSQL test over the HTTP
  path (`tests/postgres/`), not just the primitive.
- **API deprecation (planned):** datable deprecation with
  `Deprecation` / `Sunset` headers (RFC 8594) for retired fields/endpoints is
  roadmap G11; until then, breaking changes are CHANGELOG-announced.

## Accountability

- **Audit trail** records who did what, when — see
  [AUDIT_LOGGING.md](AUDIT_LOGGING.md). Tamper-evidence (hash-chain / WORM) is
  roadmap G16; today restrict DB write access and ship logs off-box.
- **Data-protection accountability** (Art. 5(2)) is the inventory + workflows in
  [PRIVACY.md](PRIVACY.md), [DATA_RETENTION.md](DATA_RETENTION.md) and
  [DATA_PROCESSING.md](DATA_PROCESSING.md).
- **Threats and their controls** are mapped in
  [THREAT_MODEL.md](THREAT_MODEL.md).

## Roles & responsibilities split

Operator vs. framework responsibilities are enumerated in
[shared-responsibility.md](shared-responsibility.md). In short: asterion provides
the controls; the operator configures, schedules, secures the infrastructure, and
maintains the legal records.
