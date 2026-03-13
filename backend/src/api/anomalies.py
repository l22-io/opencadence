from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.api.schemas import AnomalyResponse
from src.core.dependencies import JWTClaims, require_jwt


def create_anomalies_router(
    session_factory: async_sessionmaker[AsyncSession],
    jwt_secret: str,
    jwt_algorithm: str = "HS256",
) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["anomalies"])

    async def get_jwt_claims(
        authorization: str | None = Header(None),
    ) -> JWTClaims:
        return await require_jwt(
            secret=jwt_secret,
            algorithm=jwt_algorithm,
            authorization=authorization,
        )

    @router.get("/anomalies", response_model=list[AnomalyResponse])
    async def query_anomalies(
        device_id: UUID,
        start: datetime,
        end: datetime,
        metric: str | None = None,
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
        claims: JWTClaims = Depends(get_jwt_claims),  # noqa: B008
    ) -> list[AnomalyResponse]:
        if device_id not in claims.device_ids:
            raise HTTPException(
                status_code=403, detail="Device not authorized"
            )

        where = "device_id = :device_id AND time >= :start AND time < :end"
        params: dict[str, Any] = {
            "device_id": device_id,
            "start": start,
            "end": end,
            "limit": limit,
            "offset": offset,
        }
        if metric is not None:
            where += " AND metric = :metric"
            params["metric"] = metric

        stmt = text(f"""
            SELECT time, device_id, metric, value, reason, severity, context
            FROM anomalies
            WHERE {where}
            ORDER BY time DESC
            LIMIT :limit OFFSET :offset
        """)  # noqa: S608 -- where clause built from hardcoded literals
        async with session_factory() as session:
            result = await session.execute(stmt, params)
            rows = [dict(row._mapping) for row in result]

        return [AnomalyResponse(**row) for row in rows]

    return router
