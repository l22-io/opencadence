from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from src.core.auth import create_jwt_token, generate_api_key, hash_api_key
from src.core.dependencies import JWTClaims, require_api_key, require_jwt
from src.storage.models import Device

JWT_SECRET = "test-secret-key-min-32-characters-long"  # noqa: S105


@pytest.fixture
def device_with_key():
    device_id = uuid4()
    raw_key = generate_api_key(device_id)
    hashed = hash_api_key(raw_key)
    device = Device(
        id=device_id,
        name="test-device",
        api_key_hash=hashed,
        source_type="healthkit",
        revoked_at=None,
    )
    return device, raw_key


@pytest.fixture
def mock_session():
    return AsyncMock()


# --- require_api_key tests ---


@pytest.mark.asyncio
async def test_require_api_key_valid(device_with_key, mock_session) -> None:
    device, raw_key = device_with_key
    mock_session.get.return_value = device

    result = await require_api_key(api_key=raw_key, session=mock_session)
    assert result.id == device.id
    mock_session.get.assert_called_once_with(Device, device.id)


@pytest.mark.asyncio
async def test_require_api_key_missing_header(mock_session) -> None:
    with pytest.raises(HTTPException) as exc_info:
        await require_api_key(api_key=None, session=mock_session)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_require_api_key_malformed(mock_session) -> None:
    with pytest.raises(HTTPException) as exc_info:
        await require_api_key(api_key="not_a_valid_key", session=mock_session)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_require_api_key_device_not_found(mock_session) -> None:
    key = generate_api_key(uuid4())
    mock_session.get.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await require_api_key(api_key=key, session=mock_session)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_require_api_key_wrong_key(device_with_key, mock_session) -> None:
    device, _ = device_with_key
    wrong_key = generate_api_key(device.id)  # same device_id, different secret
    mock_session.get.return_value = device

    with pytest.raises(HTTPException) as exc_info:
        await require_api_key(api_key=wrong_key, session=mock_session)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_require_api_key_revoked(device_with_key, mock_session) -> None:
    device, raw_key = device_with_key
    device.revoked_at = datetime.now(UTC)
    mock_session.get.return_value = device

    with pytest.raises(HTTPException) as exc_info:
        await require_api_key(api_key=raw_key, session=mock_session)
    assert exc_info.value.status_code == 401


# --- require_jwt tests ---


@pytest.mark.asyncio
async def test_require_jwt_valid() -> None:
    device_ids = [uuid4(), uuid4()]
    token = create_jwt_token(device_ids, secret=JWT_SECRET)

    claims = await require_jwt(secret=JWT_SECRET, authorization=f"Bearer {token}")
    assert isinstance(claims, JWTClaims)
    assert claims.device_ids == device_ids


@pytest.mark.asyncio
async def test_require_jwt_missing_header() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await require_jwt(secret=JWT_SECRET, authorization=None)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_require_jwt_not_bearer() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await require_jwt(secret=JWT_SECRET, authorization="Basic abc123")
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_require_jwt_invalid_token() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await require_jwt(secret=JWT_SECRET, authorization="Bearer invalid.token.here")
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_require_jwt_wrong_secret() -> None:
    token = create_jwt_token([uuid4()], secret=JWT_SECRET)
    with pytest.raises(HTTPException) as exc_info:
        await require_jwt(
            secret="wrong-secret-key-at-least-32-chars",  # noqa: S106
            authorization=f"Bearer {token}",
        )
    assert exc_info.value.status_code == 401
