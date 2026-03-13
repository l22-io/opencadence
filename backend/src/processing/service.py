import logging
from dataclasses import dataclass
from uuid import UUID

from src.core.models import Sample
from src.core.registry import MetricRegistry
from src.metrics.instruments import ANOMALIES_FLAGGED
from src.processing.base import AnomalyFlag, BaseProcessor, ProcessingContext
from src.processing.validators import RangeValidator

logger = logging.getLogger(__name__)

# Processor class lookup
PROCESSOR_MAP: dict[str, type[BaseProcessor]] = {
    "validators.RangeValidator": RangeValidator,
}


@dataclass
class ProcessingResult:
    processed_samples: list[Sample]
    anomalies: list[tuple[Sample, AnomalyFlag]]


class ProcessingService:
    """Runs processor chains on incoming samples."""

    def __init__(self, registry: MetricRegistry) -> None:
        self._registry = registry

    def _get_processors(self, processor_names: list[str]) -> list[BaseProcessor]:
        processors: list[BaseProcessor] = []
        for name in processor_names:
            cls = PROCESSOR_MAP.get(name)
            if cls:
                processors.append(cls())
            else:
                logger.warning("Unknown processor: %s", name)
        return processors

    def process(
        self, device_id: UUID, samples: list[Sample]
    ) -> ProcessingResult:
        processed: list[Sample] = []
        all_anomalies: list[tuple[Sample, AnomalyFlag]] = []

        for sample in samples:
            metric_def = self._registry.get(sample.metric)
            if metric_def is None:
                logger.warning("Skipping unknown metric: %s", sample.metric)
                continue

            ctx = ProcessingContext(
                device_id=device_id, metric_def=metric_def
            )
            processors = self._get_processors(metric_def.processors)

            current = sample
            for proc in processors:
                current = proc.process(current, ctx)

            processed.append(current)
            for anomaly in ctx.anomalies:
                all_anomalies.append((sample, anomaly))
            if ctx.anomalies:
                for proc in processors:
                    ANOMALIES_FLAGGED.labels(
                        metric_type=sample.metric,
                        validator=type(proc).__name__,
                    ).inc(len(ctx.anomalies))

        return ProcessingResult(
            processed_samples=processed, anomalies=all_anomalies
        )
