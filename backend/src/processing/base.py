from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from uuid import UUID

from src.core.models import Sample
from src.core.registry import MetricDefinition


@dataclass
class AnomalyFlag:
    reason: str
    severity: str
    context: dict


@dataclass
class ProcessingContext:
    device_id: UUID
    metric_def: MetricDefinition
    anomalies: list[AnomalyFlag] = field(default_factory=list)


class BaseProcessor(ABC):
    @abstractmethod
    def process(self, sample: Sample, ctx: ProcessingContext) -> Sample:
        """Process a sample and return it (possibly modified).
        May add anomaly flags to ctx.anomalies."""
        ...
