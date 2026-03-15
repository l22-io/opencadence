import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.dependencies import JWTClaims, require_jwt
from src.core.events import EventBus
from src.core.models import IngestPayload
from src.ingestion.router import DataReceived

logger = logging.getLogger(__name__)


class DeadLetterResponse(BaseModel):
    id: int
    event_type: str
    payload: dict[str, Any]
    error: str
    module: str
    created_at: datetime
    replayed_at: datetime | None


class ReplayResponse(BaseModel):
    status: str
    id: int


def create_dead_letter_router(
    session_factory: async_sessionmaker[AsyncSession],
    event_bus: EventBus,
    jwt_secret: str | None = None,
    jwt_algorithm: str = "HS256",
) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["dead-letters"])

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

    @router.get("/dead-letters", response_model=list[DeadLetterResponse])
    async def list_dead_letters(
        status: str = Query(default="pending", pattern="^(pending|replayed|all)$"),
        limit: int = Query(default=50, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
        claims: JWTClaims = Depends(get_jwt_claims),  # noqa: B008
    ) -> list[DeadLetterResponse]:
        where = "1=1"
        if status == "pending":
            where = "replayed_at IS NULL"
        elif status == "replayed":
            where = "replayed_at IS NOT NULL"

        stmt = text(f"""
            SELECT id, event_type, payload, error, module, created_at, replayed_at
            FROM dead_letter
            WHERE {where}
            ORDER BY created_at DESC
            LIMIT :limit OFFSET :offset
        """)  # noqa: S608
        async with session_factory() as session:
            result = await session.execute(stmt, {"limit": limit, "offset": offset})
            rows = [dict(row._mapping) for row in result]

        return [DeadLetterResponse(**row) for row in rows]

    @router.post("/dead-letters/{dl_id}/replay", response_model=ReplayResponse)
    async def replay_dead_letter(
        dl_id: int,
        claims: JWTClaims = Depends(get_jwt_claims),  # noqa: B008
    ) -> ReplayResponse:
        async with session_factory() as session:
            result = await session.execute(
                text("SELECT id, payload, replayed_at FROM dead_letter WHERE id = :id"),
                {"id": dl_id},
            )
            row = result.first()

        if row is None:
            raise HTTPException(status_code=404, detail="Dead letter not found")

        row_map = dict(row._mapping)
        if row_map["replayed_at"] is not None:
            raise HTTPException(status_code=409, detail="Already replayed")

        payload = IngestPayload(**row_map["payload"])
        published = await event_bus.publish(DataReceived(payload=payload))
        if not published:
            raise HTTPException(status_code=503, detail="Service temporarily unavailable")

        async with session_factory() as session:
            await session.execute(
                text("UPDATE dead_letter SET replayed_at = :now WHERE id = :id"),
                {"now": datetime.now(UTC), "id": dl_id},
            )
            await session.commit()

        return ReplayResponse(status="replayed", id=dl_id)

    return router
