import logging
from dataclasses import dataclass
from uuid import UUID

from fastapi import Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import decode_jwt_token, parse_api_key, verify_api_key
from src.storage.models import Device

logger = logging.getLogger(__name__)


async def require_api_key(
    session: AsyncSession,
    api_key: str | None = Header(None, alias="X-API-Key"),
) -> Device:
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")

    device_id = parse_api_key(api_key)
    if device_id is None:
        raise HTTPException(status_code=401, detail="Invalid API key format")

    device = await session.get(Device, device_id)
    if device is None:
        raise HTTPException(status_code=401, detail="Invalid API key")

    if device.revoked_at is not None:
        raise HTTPException(status_code=401, detail="API key revoked")

    if not verify_api_key(api_key, device.api_key_hash):
        raise HTTPException(status_code=401, detail="Invalid API key")

    return device


@dataclass(frozen=True)
class JWTClaims:
    device_ids: list[UUID]


async def require_jwt(
    secret: str,
    algorithm: str = "HS256",
    authorization: str | None = Header(None),
) -> JWTClaims:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.removeprefix("Bearer ")
    payload = decode_jwt_token(token, secret=secret, algorithm=algorithm)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    device_ids = [UUID(d) for d in payload.get("device_ids", [])]
    return JWTClaims(device_ids=device_ids)
