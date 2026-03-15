from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.api.schemas import DeviceResponse
from src.core.dependencies import JWTClaims, require_jwt


def create_devices_router(
    session_factory: async_sessionmaker[AsyncSession],
    jwt_secret: str | None = None,
    jwt_algorithm: str = "HS256",
) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["devices"])

    async def get_jwt_claims(
        authorization: str | None = Header(None),
    ) -> JWTClaims:
        if jwt_secret is None:
            raise HTTPException(status_code=500, detail="Auth not configured")
        return await require_jwt(
            secret=jwt_secret,
            algorithm=jwt_algorithm,
            authorization=authorization,
        )

    @router.get("/devices", response_model=list[DeviceResponse])
    async def list_devices(
        claims: JWTClaims = Depends(get_jwt_claims),
    ) -> list[DeviceResponse]:
        stmt = text("""
            SELECT id, name, source_type, created_at, revoked_at
            FROM devices
            WHERE id = ANY(:device_ids)
            ORDER BY created_at ASC
        """)
        async with session_factory() as session:
            result = await session.execute(stmt, {"device_ids": list(claims.device_ids)})
            rows = [dict(row._mapping) for row in result]

        return [
            DeviceResponse(
                id=row["id"],
                name=row["name"],
                source_type=row["source_type"],
                created_at=row["created_at"],
                active=row["revoked_at"] is None,
            )
            for row in rows
        ]

    return router
