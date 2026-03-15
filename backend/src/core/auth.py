import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import bcrypt
from jose import JWTError, jwt  # type: ignore[import-untyped]

logger = logging.getLogger(__name__)


def hash_api_key(raw_key: str) -> str:
    return bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()


def verify_api_key(raw_key: str, hashed: str) -> bool:
    return bcrypt.checkpw(raw_key.encode(), hashed.encode())


def generate_api_key(device_id: UUID) -> str:
    suffix = secrets.token_hex(16)
    return f"oc_{device_id}_{suffix}"


def parse_api_key(raw_key: str) -> UUID | None:
    parts = raw_key.split("_", 2) if raw_key else []
    if len(parts) != 3 or parts[0] != "oc":
        return None
    try:
        return UUID(parts[1])
    except ValueError:
        return None


def create_jwt_token(
    device_ids: list[UUID],
    secret: str,
    algorithm: str = "HS256",
    expiry_hours: int = 24,
) -> str:
    payload = {
        "device_ids": [str(d) for d in device_ids],
        "exp": datetime.now(UTC) + timedelta(hours=expiry_hours),
        "iat": datetime.now(UTC),
    }
    return str(jwt.encode(payload, secret, algorithm=algorithm))


def decode_jwt_token(
    token: str,
    secret: str,
    algorithm: str = "HS256",
) -> dict[str, Any] | None:
    try:
        result: dict[str, Any] = jwt.decode(token, secret, algorithms=[algorithm])
        return result
    except JWTError:
        logger.warning("Invalid JWT token")
        return None
