# Data retention

Default retention periods, how to run the retention job, and the honest story on
how erasure interacts with backups. Companion to [PRIVACY.md](PRIVACY.md) and
[AUDIT_LOGGING.md](AUDIT_LOGGING.md).

## Defaults

All periods are [`CoreAdminConfig`](../asterion/core/config.py) fields (env-var
in brackets); change them to fit your legal basis.

| What | Config | Default | Notes |
|---|---|---|---|
| Audit logs (public + tenant) | `audit_retention_days` (`ASTERION_AUDIT_RETENTION_DAYS`) | `90` | Pruned by `audit prune` / `privacy retention-run`. |
| Auto-anonymise deactivated users | `user_anonymize_after_days` (`ASTERION_USER_ANONYMIZE_AFTER_DAYS`) | `None` | `None` = manual only. Measured from `deactivated_at`. |
| Access token | `access_token_expire_minutes` | `60` | Self-expires. |
| Refresh token | `refresh_token_expire_minutes` | `7 days` | Rotated + revoked on use. |
| Password-reset token | `password_reset_token_expire_minutes` | `30 min` | Single-use; self-expires. |
| Invite token | `invite_token_expire_minutes` | `7 days` | Single-use. |
| Revoked-token tombstones | — | until `expires_at` | Only needed until the underlying token would expire anyway. |

Token tables self-expire by timestamp; the **audit logs** and the
**deactivated-user anonymisation** are the two periods that need a scheduled job.

## Running the retention job

Two CLI entry points, both backed by
[`apply_retention`](../asterion/privacy/retention.py):

```bash
# Audit-only. Public audit_logs by default; add --all-tenants to also sweep
# every tenant schema's tenant_audit_logs (PostgreSQL). --days defaults to
# audit_retention_days.
asterion audit prune --all-tenants --yes

# Full retention run: audit prune (public + all tenants) AND — when
# user_anonymize_after_days is set — anonymise users deactivated longer ago
# than that. Idempotent.
asterion privacy retention-run --yes
```

Schedule `privacy retention-run` as a daily cron / Kubernetes CronJob. It is
idempotent (already-anonymised users are skipped via their tombstone email) and
prunes each tenant schema in its own transaction, so one tenant's failure does
not roll back the others.

```cron
# 03:30 daily
30 3 * * *  asterion privacy retention-run --yes >> /var/log/asterion-retention.log 2>&1
```

## How anonymisation works at retention time

When `user_anonymize_after_days` is set, the job selects users where
`is_active = false AND deactivated_at < now - user_anonymize_after_days` and not
already anonymised, then runs the stage-2 anonymiser (see
[PRIVACY.md — lifecycle](PRIVACY.md#data-subject-lifecycle-erasure--gdpr-art-17)):
the `users` row PII is tombstoned and the actor PII is nulled in the public and
every tenant audit log.

> Set `user_anonymize_after_days` **above** any statutory minimum-retention
> period that applies to the subject's records (working-time, payroll, tax).
> Anonymising the *account* does not erase domain rows the application must keep.

## Erasure vs. backups (the hard part)

Anonymisation and pruning act on the **live database**. They do **not** reach:

- **Point-in-time-recovery (PITR) / WAL archives** and **offline backups** taken
  before the erasure ran. A restore would resurrect the pre-erasure PII.
- **Read replicas** lag until they replay the change (normally seconds).

Until field-level encryption + crypto-shredding (roadmap **G22**) lands, asterion
**cannot** make erasure propagate into existing backups. Operators must therefore
document, in their own records of processing, one of:

1. **Backup rotation window.** "Erasure takes full effect after the backup
   retention window of *N* days, once all backups predating the erasure have
   rotated out." Keep the backup window short and bounded.
2. **Crypto-shredding (future, G22).** Per-subject/per-tenant keys; discarding
   the key renders the data unreadable everywhere, including backups.

State the chosen approach explicitly — an undocumented gap between "we erased it"
and "it's still in last night's backup" is the accountability failure.

## See also

- [PRIVACY.md](PRIVACY.md) — the lifecycle and PII inventory.
- [AUDIT_LOGGING.md](AUDIT_LOGGING.md) — what the audit rows contain.
- [`asterion/privacy/retention.py`](../asterion/privacy/retention.py).
