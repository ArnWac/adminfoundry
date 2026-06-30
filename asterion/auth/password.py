import base64
import hashlib

import bcrypt as _bcrypt


def _prehash(password: str) -> bytes:
    """Collapse an arbitrary-length password into a fixed 44-byte token.

    bcrypt silently truncates its input at 72 bytes, so two long passphrases
    that share a 72-byte prefix would hash to the same value — the full
    entropy of a long password is lost without any error. Pre-hashing with
    SHA-256 and base64-encoding (always 44 bytes, < 72) removes the cap: the
    whole password contributes to the digest. This is the standard
    bcrypt-with-pre-hash pattern (Django, passlib ``bcrypt_sha256``).
    """
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(digest)


def hash_password(password: str) -> str:
    return _bcrypt.hashpw(_prehash(password), _bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Verify ``plain`` against a stored bcrypt hash.

    Tries the current SHA-256-pre-hash scheme first. Falls back to the legacy
    scheme (raw password handed straight to bcrypt, i.e. 72-byte-truncated)
    so hashes minted before the pre-hash upgrade keep verifying — existing
    logins survive the change. The legacy check only runs when the modern
    one already failed and can therefore never weaken a new-scheme hash.
    """
    encoded = hashed.encode()
    if _bcrypt.checkpw(_prehash(plain), encoded):
        return True
    # Legacy hashes were created from the raw password, which bcrypt capped at
    # 72 bytes. Reproduce that cap explicitly: newer bcrypt raises instead of
    # truncating, so an un-truncated long input would error here rather than
    # falling through to ``False``.
    return _bcrypt.checkpw(plain.encode()[:72], encoded)


# A fixed, precomputed bcrypt hash used to equalize login timing when the email
# is unknown (Review R15). Without this, the unknown-email branch skips bcrypt
# and returns faster than a wrong-password attempt, letting an attacker
# enumerate accounts by measuring response time. It is a hard-coded constant
# (not computed at import) so importing this hot module stays cheap; the
# plaintext is irrelevant and the value is not a secret. Cost factor 12 matches
# ``hash_password``'s ``gensalt()`` default, so the dummy verify costs the same
# as a real one.
_DUMMY_HASH = "$2b$12$5FxsSUmmDFkxxqlUG5y6s.sJaHStUx.mV7W2n4pF9dBl8Fmnht2T6"


def dummy_verify_password(plain: str) -> bool:
    """Run a throwaway bcrypt verify to match the cost of :func:`verify_password`.

    Always returns ``False``. Call it on the unknown-email branch of a login so
    the response time does not reveal whether the account exists. Uses the same
    :func:`_prehash` step as the real verify's first (and usual) bcrypt call.
    """
    return _bcrypt.checkpw(_prehash(plain), _DUMMY_HASH.encode())


def validate_password_strength(password: str, *, min_length: int = 8) -> None:
    # No maximum length is enforced: the SHA-256 pre-hash in hash_password
    # removes bcrypt's 72-byte cap, so arbitrarily long passphrases are safe
    # and keep their full entropy (NIST SP 800-63B favours length).
    if len(password) < min_length:
        raise ValueError(f"Password must be at least {min_length} characters.")
