from datetime import UTC, datetime
from uuid import uuid4

from src.core.registry import FhirMapping, MetricDefinition, ValidRange
from src.fhir.mapper import to_fhir_observation


def test_map_to_fhir_observation() -> None:
    device_id = uuid4()
    metric_def = MetricDefinition(
        name="heart_rate",
        label="Heart Rate",
        unit="bpm",
        valid_range=ValidRange(min=20, max=300),
        aggregation="mean",
        processors=[],
        fhir=FhirMapping(
            code="8867-4",
            system="http://loinc.org",
            display="Heart rate",
        ),
    )

    obs = to_fhir_observation(
        device_id=device_id,
        metric_def=metric_def,
        value=72.0,
        unit="bpm",
        timestamp=datetime(2026, 3, 11, 10, 30, tzinfo=UTC),
    )

    assert obs["resourceType"] == "Observation"
    assert obs["status"] == "final"
    assert obs["code"]["coding"][0]["code"] == "8867-4"
    assert obs["valueQuantity"]["value"] == 72.0
    assert obs["valueQuantity"]["unit"] == "bpm"
    assert obs["device"]["reference"] == f"Device/{device_id}"
