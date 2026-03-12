from uuid import uuid4

import pytest

from src.core.auth import (
    create_jwt_token,
    decode_jwt_token,
    hash_api_key,
    verify_api_key,
)


def test_hash_and_verify_api_key() -> None:
    raw_key = "oc_test_key_abc123"
    hashed = hash_api_key(raw_key)
    assert verify_api_key(raw_key, hashed) is True
    assert verify_api_key("wrong_key", hashed) is False


def test_create_and_decode_jwt() -> None:
    device_ids = [uuid4(), uuid4()]
    secret = "test-secret-key-min-32-characters-long"
    token = create_jwt_token(
        device_ids=device_ids,
        secret=secret,
        algorithm="HS256",
        expiry_hours=24,
    )
    payload = decode_jwt_token(token, secret=secret, algorithm="HS256")
    assert payload is not None
    decoded_ids = [str(d) for d in device_ids]
    assert payload["device_ids"] == decoded_ids


def test_decode_invalid_jwt() -> None:
    secret = "test-secret-key-min-32-characters-long"
    payload = decode_jwt_token("invalid.token.here", secret=secret, algorithm="HS256")
    assert payload is None
