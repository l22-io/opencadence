from datetime import UTC, datetime
from uuid import uuid4

from src.core.models import Sample
from src.core.registry import MetricDefinition, ValidRange, FhirMapping
from src.processing.base import ProcessingContext, AnomalyFlag
from src.processing.validators import RangeValidator


def _make_metric() -> MetricDefinition:
    return MetricDefinition(
        name="heart_rate",
        label="Heart Rate",
        unit="bpm",
        valid_range=ValidRange(min=20, max=300),
        aggregation="mean",
        processors=["validators.RangeValidator"],
        fhir=FhirMapping(code="8867-4", system="http://loinc.org", display="Heart rate"),
    )


def test_range_validator_passes_valid() -> None:
    validator = RangeValidator()
    sample = Sample(
        metric="heart_rate", value=72.0, unit="bpm",
        timestamp=datetime.now(UTC), source="test",
    )
    ctx = ProcessingContext(
        device_id=uuid4(), metric_def=_make_metric(), anomalies=[]
    )
    result = validator.process(sample, ctx)
    assert result == sample
    assert len(ctx.anomalies) == 0


def test_range_validator_flags_out_of_range() -> None:
    validator = RangeValidator()
    sample = Sample(
        metric="heart_rate", value=350.0, unit="bpm",
        timestamp=datetime.now(UTC), source="test",
    )
    ctx = ProcessingContext(
        device_id=uuid4(), metric_def=_make_metric(), anomalies=[]
    )
    result = validator.process(sample, ctx)
    assert result == sample  # sample passes through, but anomaly is flagged
    assert len(ctx.anomalies) == 1
    assert ctx.anomalies[0].reason == "out_of_range"
