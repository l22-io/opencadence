import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import bcrypt
from jose import JWTError, jwt

logger = logging.getLogger(__name__)


def hash_api_key(raw_key: str) -> str:
    return bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()


def verify_api_key(raw_key: str, hashed: str) -> bool:
    return bcrypt.checkpw(raw_key.encode(), hashed.encode())


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
    return jwt.encode(payload, secret, algorithm=algorithm)


def decode_jwt_token(
    token: str,
    secret: str,
    algorithm: str = "HS256",
) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, secret, algorithms=[algorithm])
    except JWTError:
        logger.warning("Invalid JWT token")
        return None
