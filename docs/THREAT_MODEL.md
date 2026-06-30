# Threat model (STRIDE-light)

A pragmatic threat model for the asterion framework: the assets, trust
boundaries, and a STRIDE pass mapping each threat class to the control that
addresses it and the residual gap. This is the framework layer; an embedding app
adds its own domain threats.

## Assets

- **Tenant data** (per-schema operational data — the crown jewels).
- **Credentials** (`hashed_password`, `totp_secret`, reset/backup-code hashes).
- **Bearer tokens** (access / refresh / impersonation / MFA-challenge JWTs).
- **Audit trail** (accountability record).
- **PII** (see [PRIVACY.md](PRIVACY.md)).

## Trust boundaries

```
 untrusted          │ trusted (app process)          │ trusted (data)
 client / browser ──┼─► FastAPI + auth + RBAC ────────┼─► PostgreSQL (schema/tenant)
 reverse proxy    ──┘   middleware, validation        └─► sub-processors (opt-in)
```

The client is never trusted: every request re-authenticates (stateless JWT) and
re-authorises. The reverse proxy is trusted only up to `trusted_proxy_count` hops
for client-IP derivation.

## STRIDE pass

| Threat | Vector | Control | Residual / reference |
|---|---|---|---|
| **Spoofing** | Forged identity / stolen token | JWT signature; `token_version` (logout-all) + per-`jti` revocation checked every request; bcrypt+SHA-256 password hashing; optional 2FA; optional `iss`/`aud` pinning | Token theft via XSS if UI keeps token in `localStorage` → set a strict CSP; the bundled UI is nonce-hardened (G10) so `script-src 'self' 'nonce-{nonce}'` covers it. [security.md](security.md#known-limitations) |
| **Tampering** | Mutate data / audit rows | Tenant RBAC + protected fields + readonly fields; input validation; CRUD policies tighten-only | Audit rows are mutable (no WORM) → G16; restrict DB write. [AUDIT_LOGGING.md](AUDIT_LOGGING.md#tamper-evidence-limitation) |
| **Repudiation** | "I didn't do that" | Audit trail per event with actor + IP; impersonation reason (G9) | Tamper-evidence pending (G16). |
| **Information disclosure** | Cross-tenant leak / PII exposure | **Schema-per-tenant** `search_path` isolation (CI-proven on real PG); K3 write-guard; protected-field masking in contract/serializer/writes; secret + PII redaction in audit/logs | Field-level encryption at rest is G22 → rely on infra encryption. [tenancy.md](tenancy.md) |
| **Denial of service** | Credential stuffing / reset-bombing / noisy neighbour | Login rate limiter; password-reset throttle (per email); 2FA-login throttle | In-memory limiter is per-process (use Redis backend for multi-worker); **no per-tenant API quota yet** (G19). [security.md](security.md#login-rate-limiting) |
| **Elevation of privilege** | Gain admin / cross-tenant | Superadmin-gated root scope; impersonation tokens rejected at root; permission keys allow trailing-wildcard only; `single_tenant_require_superadmin` default | All-or-nothing superadmin (no least-privilege support role yet → G14). [permission-matrix.md](permission-matrix.md) |

## Key invariants (must not regress)

1. **Tenant isolation is structural** (`SET LOCAL search_path`), not a Python
   filter. Tenant tables carry no `tenant_id`. Verified in `tests/postgres/`.
2. **Protected fields never leak** — enforced in contract, serializer, and the
   write validator alike.
3. **Policies can only tighten** field/object access, never loosen.
4. **Impersonation cannot use root** — `require_superadmin` rejects impersonation
   tokens.

A change that weakens any of these needs an ADR and a test proving the new
boundary.

## Known gaps (tracked)

| Gap | Roadmap |
|---|---|
| Audit tamper-evidence (hash-chain / WORM / legal hold) | G16 |
| Field encryption + crypto-shredding (erasure in backups) | G22 |
| Per-tenant rate limiting / quotas | G19 |
| Least-privilege global "Support" role | G14 |
| RLS as defence-in-depth behind schema isolation | G15 |

## See also

- [security.md](security.md) · [GOVERNANCE.md](GOVERNANCE.md) ·
  [DATA_PROCESSING.md](DATA_PROCESSING.md) · [roadmap.md](roadmap.md)
