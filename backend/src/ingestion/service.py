from datetime import UTC, datetime, timedelta

from src.core.models import IngestPayload
from src.core.registry import MetricRegistry


class ValidationError(Exception):
    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__(f"Validation failed: {errors}")


class IngestionService:
    """Validates and normalizes incoming health data."""

    # Allow timestamps up to 5 minutes in the future (clock skew)
    MAX_FUTURE_OFFSET = timedelta(minutes=5)

    def __init__(self, registry: MetricRegistry) -> None:
        self._registry = registry

    def validate(self, payload: IngestPayload) -> list[str]:
        errors: list[str] = []
        now = datetime.now(UTC)

        for i, sample in enumerate(payload.batch):
            metric_def = self._registry.get(sample.metric)
            if metric_def is None:
                errors.append(f"Sample {i}: unknown metric '{sample.metric}'")
                continue

            if sample.timestamp > now + self.MAX_FUTURE_OFFSET:
                errors.append(f"Sample {i}: future timestamp {sample.timestamp.isoformat()}")

        return errors
