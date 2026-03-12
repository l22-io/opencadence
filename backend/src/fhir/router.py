from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.dependencies import JWTClaims, require_jwt
from src.core.registry import MetricRegistry
from src.fhir.mapper import to_fhir_observation
from src.storage.repository import SampleRepository


def create_fhir_router(
    session_factory: async_sessionmaker[AsyncSession],
    repo: SampleRepository,
    registry: MetricRegistry,
    jwt_secret: str | None = None,
    jwt_algorithm: str = "HS256",
) -> APIRouter:
    router = APIRouter(prefix="/fhir", tags=["fhir"])

    async def get_jwt_claims(
        authorization: str | None = Header(None),
    ) -> JWTClaims:
        if jwt_secret is None:
            raise HTTPException(status_code=500, detail="Auth not configured")
        return await require_jwt(
            secret=jwt_secret, algorithm=jwt_algorithm, authorization=authorization,
        )

    @router.get("/Observation")
    async def get_observations(
        device_id: UUID,
        metric: str,
        start: datetime,
        end: datetime,
        _count: int = Query(default=100, alias="_count", le=1000),
        claims: JWTClaims = Depends(get_jwt_claims),
    ) -> dict[str, Any]:
        if device_id not in claims.device_ids:
            raise HTTPException(
                status_code=403, detail="Token does not grant access to this device"
            )

        metric_def = registry.get(metric)
        if metric_def is None:
            return {"resourceType": "Bundle", "type": "searchset", "total": 0, "entry": []}

        async with session_factory() as session:
            rows = await repo.query_raw(
                session, device_id, metric, start, end, limit=_count
            )

        entries = [
            {
                "resource": to_fhir_observation(
                    device_id=device_id,
                    metric_def=metric_def,
                    value=row["value"],
                    unit=row["unit"],
                    timestamp=row["time"],
                ),
            }
            for row in rows
        ]

        return {
            "resourceType": "Bundle",
            "type": "searchset",
            "total": len(entries),
            "entry": entries,
        }

    return router
