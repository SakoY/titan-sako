"""Tests for app/core/security.py (TASK-017)."""

import hashlib
import hmac

from app.core.security import generate_api_key, hash_pii


# ---------------------------------------------------------------------------
# hash_pii
# ---------------------------------------------------------------------------


def test_hash_pii_returns_hex_string():
    result = hash_pii("user@example.com", "secret")
    assert isinstance(result, str)
    assert all(c in "0123456789abcdef" for c in result)


def test_hash_pii_deterministic():
    assert hash_pii("user@example.com", "secret") == hash_pii("user@example.com", "secret")


def test_hash_pii_different_values_produce_different_hashes():
    assert hash_pii("a@example.com", "secret") != hash_pii("b@example.com", "secret")


def test_hash_pii_different_keys_produce_different_hashes():
    assert hash_pii("user@example.com", "key1") != hash_pii("user@example.com", "key2")


def test_hash_pii_matches_hmac_sha256():
    value = "patron@library.org"
    key = "supersecret"
    expected = hmac.new(key.encode(), value.encode(), hashlib.sha256).hexdigest()
    assert hash_pii(value, key) == expected


def test_hash_pii_returns_64_char_hex():
    # SHA-256 produces 32 bytes → 64 hex chars
    result = hash_pii("any", "key")
    assert len(result) == 64


# ---------------------------------------------------------------------------
# generate_api_key
# ---------------------------------------------------------------------------


def test_generate_api_key_returns_string():
    assert isinstance(generate_api_key(), str)


def test_generate_api_key_is_url_safe():
    key = generate_api_key()
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
    assert all(c in allowed for c in key)


def test_generate_api_key_minimum_length():
    # token_urlsafe(32) encodes 32 bytes → at least 43 base64url chars
    assert len(generate_api_key()) >= 43


def test_generate_api_key_is_unique():
    keys = {generate_api_key() for _ in range(100)}
    assert len(keys) == 100
