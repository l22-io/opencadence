from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Query
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.api.schemas import (
    AggregatedSample,
    AnomalyResponse,
    DataQueryResponse,
    RawSample,
)
from src.storage.repository import SampleRepository


def create_api_router(
    session_factory: async_sessionmaker[AsyncSession],
    repo: SampleRepository,
) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["query"])

    @router.get("/data", response_model=DataQueryResponse)
    async def query_data(
        device_id: UUID,
        metric: str,
        start: datetime,
        end: datetime,
        resolution: str = Query(default="raw", pattern="^(raw|1min|1hr)$"),
    ) -> DataQueryResponse:
        async with session_factory() as session:
            if resolution == "raw":
                rows = await repo.query_raw(session, device_id, metric, start, end)
                samples = [
                    RawSample(
                        time=r["time"], value=r["value"],
                        unit=r["unit"], source=r["source"],
                    )
                    for r in rows
                ]
            else:
                rows = await repo.query_aggregates(
                    session, device_id, metric, start, end, resolution
                )
                samples = [
                    AggregatedSample(
                        time=r["time"],
                        min=r["min_value"],
                        max=r["max_value"],
                        mean=r["mean_value"],
                        stddev=r["stddev_value"],
                        count=r["sample_count"],
                    )
                    for r in rows
                ]

        return DataQueryResponse(
            device_id=device_id,
            metric=metric,
            resolution=resolution,
            samples=samples,
        )

    return router
