# Shared responsibility

asterion is a **framework** you embed and operate, not a hosted service. This
table splits what the framework provides from what the operator must configure,
schedule, and secure. "Operator" = whoever runs the deployment (you, or the SaaS
provider embedding asterion); they are the processor toward end customers.

## Split of responsibilities

| Area | asterion provides | Operator owns |
|---|---|---|
| **Authentication** | JWT issuance/validation, bcrypt+SHA-256 hashing, optional 2FA, token revocation (`token_version` + per-`jti`) | Secret-key management + rotation; HTTPS; choosing/operating an external IdP if used |
| **Authorization** | Tenant RBAC, permission keys, protected fields, tighten-only policies, superadmin-gated root | Assigning roles; deciding `single_tenant_require_superadmin`; who is superadmin |
| **Tenant isolation** | Schema-per-tenant `search_path` isolation; K3 write guard; CI proof | Running PostgreSQL (SQLite is dev/test only); not bypassing the session helpers |
| **Privacy / erasure** | Two-stage anonymisation (G2), PII registry (G1), audit redaction (G7) | Classifying app PII; setting `user_anonymize_after_days`; scheduling `privacy retention-run`; legal retention basis |
| **Audit** | Per-event trail, redaction pipeline, retention job | Scheduling pruning; off-box log shipping; restricting DB write (tamper) |
| **Rate limiting** | Login + password-reset + 2FA throttles (in-memory default) | Wiring a Redis backend for multi-worker; per-tenant quotas (app/proxy, G19 pending) |
| **Transport security** | Emits bearer tokens; security headers (opt-in CSP) | TLS termination; `--proxy-headers` + `trusted_proxy_count`; setting a CSP |
| **Data at rest** | App stores via SQLAlchemy | DB/disk encryption; object-store encryption; backup/PITR strategy |
| **Sub-processors** | Opt-in adapters (S3, SMTP/Resend/SES, OAuth, Redis) | Choosing them; DPAs with each; declaring them ([DATA_PROCESSING.md](DATA_PROCESSING.md)) |
| **Backups / erasure-in-backups** | Live-DB erasure only | Backup rotation window documentation (G22 crypto-shredding pending) |
| **Availability** | Stateless app, pooled DB | HA topology, monitoring, capacity, DR |
| **Legal records** | Technical building blocks + templates | RoPA, DPAs, TOMs sign-off, works-council agreements |

## Deployment-time checklist (operator)

- [ ] `secret_key` ≥ 32 chars, from a secret manager; `environment=production`.
- [ ] PostgreSQL (not SQLite); DB-level encryption + backups + bounded PITR.
- [ ] HTTPS everywhere; `uvicorn --proxy-headers` + `trusted_proxy_count` set to
      the real hop count.
- [ ] `content_security_policy` set — with the bundled UI include `{nonce}` in
      `script-src` (G10); API-first deployments can use any static strict policy.
- [ ] Redis rate-limit backend if running multiple workers.
- [ ] `privacy retention-run` scheduled; `user_anonymize_after_days` set above
      any statutory minimum.
- [ ] Audit logs shipped off-box; DB write access restricted.
- [ ] Sub-processor DPAs in place for every enabled external service.
- [ ] CI runs `pytest -m postgres` to keep the isolation proof live.

See [deployment.md](deployment.md) for the production guardrails asterion
enforces at startup (e.g. it refuses to boot on SQLite or with a weak secret in
`production`).

## See also

- [GOVERNANCE.md](GOVERNANCE.md) · [DATA_PROCESSING.md](DATA_PROCESSING.md) ·
  [security.md](security.md) · [deployment.md](deployment.md)
