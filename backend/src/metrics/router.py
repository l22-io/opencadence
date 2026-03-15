from typing import Any

from fastapi import APIRouter, Header, HTTPException, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from src.metrics.instruments import collect_infra_metrics


def create_metrics_router(
    engine: Any,
    redis: Any,
    event_bus: Any,
    metrics_token: str | None = None,
) -> APIRouter:
    router = APIRouter(tags=["metrics"])

    @router.get("/metrics")
    async def metrics(
        authorization: str | None = Header(None),
    ) -> Response:
        if metrics_token is not None:
            expected = f"Bearer {metrics_token}"
            if authorization != expected:
                raise HTTPException(status_code=401, detail="Unauthorized")

        await collect_infra_metrics(engine=engine, redis=redis, event_bus=event_bus)

        return Response(
            content=generate_latest(),
            media_type=CONTENT_TYPE_LATEST,
        )

    return router
