"""Security utilities — PII hashing and API key helpers."""

import hashlib
import hmac
import secrets


def hash_pii(value: str, secret_key: str) -> str:
    """
    HMAC-SHA256 hash of value keyed with secret_key.
    Deterministic (same input + key → same output) and irreversible.
    """
    return hmac.new(
        secret_key.encode(),
        value.encode(),
        hashlib.sha256,
    ).hexdigest()


def generate_api_key() -> str:
    """Generate a cryptographically random plaintext API key."""
    return secrets.token_urlsafe(32)
