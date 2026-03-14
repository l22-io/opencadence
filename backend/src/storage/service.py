import json
import logging
import traceback

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.core.models import IngestPayload
from src.core.registry import MetricRegistry
from src.metrics.instruments import DEAD_LETTERS_TOTAL
from src.processing.service import ProcessingService
from src.storage.repository import SampleRepository

logger = logging.getLogger(__name__)


class StorageService:
    """Subscribes to events and persists data to TimescaleDB."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        registry: MetricRegistry,
    ) -> None:
        self._session_factory = session_factory
        self._repo = SampleRepository()
        self._processing = ProcessingService(registry=registry)

    async def handle_data_received(self, payload: IngestPayload) -> None:
        """Process and store incoming data."""
        try:
            result = self._processing.process(payload.device_id, payload.batch)

            async with self._session_factory() as session:
                # Store raw samples
                if result.processed_samples:
                    insert_payload = IngestPayload(
                        device_id=payload.device_id,
                        batch=result.processed_samples,
                    )
                    count = await self._repo.insert_samples(session, insert_payload)
                    logger.info("Stored %d samples for device %s", count, payload.device_id)

                # Store anomalies
                for sample, anomaly in result.anomalies:
                    await session.execute(
                        text("""
                            INSERT INTO anomalies
                            (time, device_id, metric, value, reason, severity, context)
                            VALUES (:time, :device_id, :metric, :value,
                                    :reason, :severity, :context::jsonb)
                        """),
                        {
                            "time": sample.timestamp,
                            "device_id": payload.device_id,
                            "metric": sample.metric,
                            "value": sample.value,
                            "reason": anomaly.reason,
                            "severity": anomaly.severity,
                            "context": json.dumps(anomaly.context),
                        },
                    )
                if result.anomalies:
                    await session.commit()
                    logger.info(
                        "Flagged %d anomalies for device %s",
                        len(result.anomalies),
                        payload.device_id,
                    )
        except Exception as exc:
            logger.exception("Failed to process data for device %s", payload.device_id)
            # Persist to dead letter queue
            async with self._session_factory() as dl_session:
                await dl_session.execute(
                    text("""
                        INSERT INTO dead_letter (event_type, payload, error, module)
                        VALUES (:event_type, :payload::jsonb, :error, :module)
                    """),
                    {
                        "event_type": "DataReceived",
                        "payload": json.dumps(payload.model_dump(mode="json")),
                        "error": f"{exc}\n{traceback.format_exc()}",
                        "module": "storage",
                    },
                )
                await dl_session.commit()
            DEAD_LETTERS_TOTAL.inc()
            logger.info("Dead letter persisted for device %s", payload.device_id)
