import logging
from dataclasses import dataclass
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ValidRange:
    min: float
    max: float


@dataclass(frozen=True)
class FhirMapping:
    code: str
    system: str
    display: str


@dataclass(frozen=True)
class MetricDefinition:
    name: str
    label: str
    unit: str
    valid_range: ValidRange
    aggregation: str
    processors: list[str]
    fhir: FhirMapping

    def is_in_range(self, value: float) -> bool:
        return self.valid_range.min <= value <= self.valid_range.max


class MetricRegistry:
    """Loads and provides access to metric definitions from YAML files."""

    def __init__(self, metrics: dict[str, MetricDefinition]) -> None:
        self._metrics = metrics

    @classmethod
    def from_directory(cls, path: Path) -> "MetricRegistry":
        metrics: dict[str, MetricDefinition] = {}
        for yaml_file in sorted(path.glob("*.yaml")):
            try:
                with open(yaml_file) as f:
                    data = yaml.safe_load(f)
                definition = MetricDefinition(
                    name=data["name"],
                    label=data["label"],
                    unit=data["unit"],
                    valid_range=ValidRange(
                        min=data["valid_range"]["min"],
                        max=data["valid_range"]["max"],
                    ),
                    aggregation=data["aggregation"],
                    processors=data.get("processors", []),
                    fhir=FhirMapping(
                        code=data["fhir"]["code"],
                        system=data["fhir"]["system"],
                        display=data["fhir"]["display"],
                    ),
                )
                metrics[definition.name] = definition
                logger.info("Loaded metric: %s", definition.name)
            except (KeyError, TypeError) as e:
                logger.error("Invalid metric definition in %s: %s", yaml_file, e)
                raise ValueError(f"Invalid metric definition in {yaml_file}: {e}") from e
        return cls(metrics)

    def get(self, name: str) -> MetricDefinition | None:
        return self._metrics.get(name)

    def list_metrics(self) -> list[str]:
        return list(self._metrics.keys())
