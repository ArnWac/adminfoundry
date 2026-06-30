"""User-lifecycle stage 2 — anonymisation (roadmap G2, DSGVO Art. 17).

Stage 1 (deactivation: ``is_active=False`` + ``token_version++``) already
exists and is reversible. This module supplies **stage 2**: the irreversible
removal of personal data once a retention period has elapsed.

Why anonymise instead of hard-delete: only ``tenant_membership.user_id`` carries
a real foreign key; every other user reference is an FK-less column
(``audit_logs.actor_user_id`` + ``actor_label``, ``impersonation_logs.*``,
``saved_filters.user_id`` …). A row ``DELETE`` would orphan those references and
— worse — leave the actor's e-mail behind in ``actor_label`` (an *incomplete*
erasure). Keeping the row and overwriting the PII in place satisfies Art. 17
while preserving audit/foreign-key integrity.

Two operations, deliberately separate so the retention job can compose them per
schema:

* :func:`anonymize_user` — tombstones PII on the ``users`` row,
* :func:`anonymize_audit_actor` — nulls the actor PII left in the audit tables.
"""

from __future__ import annotations

import secrets
import uuid
from typing import Any, cast

from sqlalchemy import CursorResult, update
from sqlalchemy.ext.asyncio import AsyncSession

from asterion.auth.password import hash_password
from asterion.models.audit_log import AuditLog
from asterion.models.tenant_audit_log import TenantAuditLog
from asterion.models.user import User

#: Reserved-by-RFC-2606 TLD: a tombstone address can never route to a real
#: inbox, yet stays unique per user so the ``users.email`` UNIQUE constraint is
#: preserved after anonymisation.
ANONYMIZED_EMAIL_DOMAIN = "anonymized.invalid"


def anonymized_email(user_id: uuid.UUID) -> str:
    """Deterministic, unroutable tombstone address for ``user_id``."""
    return f"anonymized-{user_id}@{ANONYMIZED_EMAIL_DOMAIN}"


def anonymize_user(user: User) -> dict[str, Any]:
    """Irreversibly tombstone every PII field on ``user`` *in place*.

    The row survives (audit/FK integrity); only the personal data is destroyed:

    * ``email`` → deterministic ``anonymized-<id>@anonymized.invalid`` tombstone,
    * ``full_name`` / ``totp_secret`` → cleared, ``totp_enabled`` → False,
    * ``hashed_password`` → a fresh hash of a random, immediately-discarded
      secret, so the column holds no recoverable value and login can never
      succeed,
    * ``is_active=False`` + ``token_version`` bump → any live token dies.

    Returns a **PII-free** summary suitable for the audit ``changes`` field.
    """
    user.email = anonymized_email(user.id)
    user.full_name = None
    user.totp_secret = None
    user.totp_enabled = False
    # A valid-but-unknowable bcrypt hash: verify_password runs normally and
    # always returns False, instead of an invalid hash string that could make
    # bcrypt raise.
    user.hashed_password = hash_password(secrets.token_urlsafe(32))
    user.is_active = False
    user.token_version = (user.token_version or 0) + 1
    return {"user_id": str(user.id), "anonymized": True}


async def anonymize_audit_actor(
    session: AsyncSession,
    actor_user_id: uuid.UUID,
    *,
    tenant_scoped: bool = False,
) -> int:
    """Strip the actor's PII (``actor_label`` e-mail, ``ip_address``) from audit rows.

    Operates on the audit table reachable through ``session``: the public
    :class:`AuditLog` by default, or :class:`TenantAuditLog` (inside the active
    tenant schema) when ``tenant_scoped`` is True — the retention job iterates
    tenant schemas and calls it once per schema. The audit *rows* survive
    (action / ``actor_user_id`` / timestamp keep the trail intact); only the
    embedded personal data is nulled. Returns the number of rows touched.
    """
    model = TenantAuditLog if tenant_scoped else AuditLog
    result = await session.execute(
        update(model)
        .where(model.actor_user_id == actor_user_id)
        .values(actor_label=None, ip_address=None)
    )
    rowcount = cast("CursorResult[Any]", result).rowcount
    return rowcount if rowcount is not None else 0
