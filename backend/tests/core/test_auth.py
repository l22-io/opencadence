from uuid import uuid4

import pytest

from src.core.auth import (
    create_jwt_token,
    decode_jwt_token,
    generate_api_key,
    hash_api_key,
    parse_api_key,
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


def test_generate_api_key_format() -> None:
    device_id = uuid4()
    key = generate_api_key(device_id)
    assert key.startswith(f"oc_{device_id}_")
    suffix = key.split("_", 2)[2]
    # 32 hex chars after the device_id prefix
    assert len(suffix) == 32
    int(suffix, 16)  # must be valid hex


def test_generate_api_key_unique() -> None:
    device_id = uuid4()
    key1 = generate_api_key(device_id)
    key2 = generate_api_key(device_id)
    assert key1 != key2


def test_parse_api_key_valid() -> None:
    device_id = uuid4()
    key = generate_api_key(device_id)
    parsed = parse_api_key(key)
    assert parsed == device_id


def test_parse_api_key_invalid() -> None:
    assert parse_api_key("invalid_key") is None
    assert parse_api_key("oc_not-a-uuid_abcd1234") is None
    assert parse_api_key("") is None
