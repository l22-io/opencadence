from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.models import IngestPayload


class SampleRepository:
    """Data access for raw samples and aggregates."""

    @staticmethod
    def payload_to_rows(payload: IngestPayload) -> list[dict[str, Any]]:
        return [
            {
                "time": sample.timestamp,
                "device_id": payload.device_id,
                "metric": sample.metric,
                "value": sample.value,
                "unit": sample.unit,
                "source": sample.source,
            }
            for sample in payload.batch
        ]

    async def insert_samples(
        self, session: AsyncSession, payload: IngestPayload
    ) -> int:
        rows = self.payload_to_rows(payload)
        stmt = text("""
            INSERT INTO raw_samples (time, device_id, metric, value, unit, source)
            VALUES (:time, :device_id, :metric, :value, :unit, :source)
            ON CONFLICT (time, device_id, metric, source) DO NOTHING
        """)
        result = await session.execute(stmt, rows)
        await session.commit()
        return result.rowcount  # type: ignore[return-value]

    async def query_raw(
        self,
        session: AsyncSession,
        device_id: UUID,
        metric: str,
        start: datetime,
        end: datetime,
        limit: int = 10000,
    ) -> list[dict[str, Any]]:
        stmt = text("""
            SELECT time, value, unit, source
            FROM raw_samples
            WHERE device_id = :device_id AND metric = :metric
              AND time >= :start AND time < :end
            ORDER BY time
            LIMIT :limit
        """)
        result = await session.execute(
            stmt,
            {"device_id": device_id, "metric": metric, "start": start, "end": end, "limit": limit},
        )
        return [dict(row._mapping) for row in result]

    async def query_aggregates(
        self,
        session: AsyncSession,
        device_id: UUID,
        metric: str,
        start: datetime,
        end: datetime,
        resolution: str,
    ) -> list[dict[str, Any]]:
        allowed_views = {"1min": "aggregates_1min", "1hr": "aggregates_1hr"}
        view = allowed_views.get(resolution)
        if view is None:
            raise ValueError(f"Invalid resolution: {resolution}")
        stmt = text(f"""
            SELECT bucket AS time, min_value, max_value, mean_value,
                   stddev_value, sample_count
            FROM {view}
            WHERE device_id = :device_id AND metric = :metric
              AND bucket >= :start AND bucket < :end
            ORDER BY bucket
        """)
        result = await session.execute(
            stmt,
            {"device_id": device_id, "metric": metric, "start": start, "end": end},
        )
        return [dict(row._mapping) for row in result]

    async def query_devices(
        self,
        session: AsyncSession,
        device_ids: list[UUID],
    ) -> list[dict[str, Any]]:
        stmt = text("""
            SELECT id, name, source_type, created_at, revoked_at
            FROM devices
            WHERE id = ANY(:device_ids)
            ORDER BY created_at ASC
        """)
        result = await session.execute(stmt, {"device_ids": device_ids})
        return [dict(row._mapping) for row in result]
