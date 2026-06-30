# Audit logging

What asterion records in its audit trail, what it deliberately does **not**
record, how values are minimised before they hit the database, retention, and
the tamper-evidence limitation. Companion to [security.md](security.md),
[PRIVACY.md](PRIVACY.md) and [DATA_RETENTION.md](DATA_RETENTION.md).

## What is logged

One row per security-relevant event, written by
[`asterion/audit/service.py`](../asterion/audit/service.py):

| Event | Action constant |
|---|---|
| Login success / failure | `login_success` / `login_failure` |
| Logout / logout-everywhere | `logout` / `logout_all` |
| Password-reset request / confirm | `password_reset_request` / `password_reset_confirm` |
| 2FA enable / disable | `two_factor_enabled` / `two_factor_disabled` |
| CRUD create / update / delete | `crud_create` / `crud_update` / `crud_delete` |
| Admin action | `admin_action` |
| Impersonation start / stop | `impersonation_start` / `impersonation_stop` |
| Superadmin tenant access | `tenant_access` |
| User anonymisation (G2) | `user_anonymize` |

Each row carries: `method`, `path`, `status_code`, `actor_user_id`,
`actor_label` (actor email snapshot), `ip_address`, `resource`, `record_id`,
`action`, and a `changes` diff.

### Two destinations

- **Global / cross-tenant events** (login, impersonation, user/tenant
  management) → `public.audit_logs`, with `tenant_id` as a discriminator column.
- **Tenant-context events** (CRUD / actions on tenant resources) →
  `tenant_audit_logs` **inside the tenant schema** — no `tenant_id` column, the
  schema *is* the tenant. The writer asserts the `search_path` points at a
  tenant schema first (K3 guard), so a misconfigured write is skipped rather
  than landing in the wrong schema.

### Write modes

- **In-session, savepoint-isolated** (`record_audit_in_session`) for CRUD /
  actions: the row commits with the main transaction; an audit-insert failure is
  caught and never breaks the response.
- **Isolated session** (`record_audit`) for login and CLI paths that must record
  even when the surrounding request raises.

An audit miss is logged and swallowed — it never surfaces as a 500.

## What is NOT logged / is minimised

`changes` passes through **three** passes before insert (in order):

1. **Secret stripping** — [`sanitize_payload`](../asterion/security/sanitize.py)
   redacts values under secret-ish keys (`password`, `*_token`, `secret`,
   `authorization`, `api_key`, …) → `***REDACTED***`. Recursive.
2. **PII masking (G7)** — values of fields classified `IDENTITY` / `CONTACT` /
   `SENSITIVE` in the [PII registry](../asterion/privacy/classification.py) are
   masked per `audit_pii_mode` (`redact` default → `***PII***`; `hash` → a short
   SHA-256 tag; `keep` → raw). So `email` / `full_name` diffs are `***PII***` by
   default.
3. **Behavioural suppression (G5)** — values of `BEHAVIORAL`-classified fields
   are suppressed (`***BEHAVIORAL***`) unless `audit_behavioral_detail=True`. The
   row keeps *that* the field changed, not the value (§26 BDSG / Art. 88).

`actor_label` (the audit's WHO column) is **not** masked — identifying the actor
is the point of the trail. It is nulled only on subject anonymisation (G2).

> The three passes are configured once at startup (process-wide defaults from
> config); the audit writer's many call sites need no per-call wiring. Secure
> defaults (`redact` + suppress) apply even before `create_admin` runs.

## Retention

`audit_retention_days` (default 90) bounds growth and satisfies storage
limitation (Art. 5) per tenant. Run `asterion audit prune --all-tenants` or
`asterion privacy retention-run` on a schedule — see
[DATA_RETENTION.md](DATA_RETENTION.md). Without a scheduled job the tables grow
unbounded.

## Tamper evidence (limitation)

Audit rows are **mutable and prunable** — there is no hash-chain, WORM storage,
or legal-hold today (roadmap **G16**). The trail is suitable for operational
forensics and accountability, **not** as tamper-proof evidence for a regulated
context that requires append-only guarantees. A database administrator with
write access can alter rows. Mitigate operationally with restricted DB
privileges, off-box log shipping (SIEM), and PITR until G16 lands.

## See also

- [security.md — Audit](security.md#audit)
- [`asterion/audit/service.py`](../asterion/audit/service.py),
  [`asterion/privacy/redaction.py`](../asterion/privacy/redaction.py).
