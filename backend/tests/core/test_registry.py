from pathlib import Path

import pytest

from src.core.registry import MetricDefinition, MetricRegistry


@pytest.fixture
def registry(tmp_path: Path) -> MetricRegistry:
    """Create a registry with a test metric YAML."""
    metric_file = tmp_path / "test_metric.yaml"
    metric_file.write_text("""
name: test_metric
label: Test Metric
unit: units
valid_range:
  min: 0
  max: 100
aggregation: mean
processors:
  - validators.RangeValidator
fhir:
  code: "12345-6"
  system: "http://loinc.org"
  display: "Test Metric"
""")
    return MetricRegistry.from_directory(tmp_path)


def test_registry_loads_metric(registry: MetricRegistry) -> None:
    metric = registry.get("test_metric")
    assert metric is not None
    assert metric.name == "test_metric"
    assert metric.label == "Test Metric"
    assert metric.unit == "units"
    assert metric.valid_range.min == 0
    assert metric.valid_range.max == 100


def test_registry_unknown_metric(registry: MetricRegistry) -> None:
    assert registry.get("nonexistent") is None


def test_registry_lists_all_metrics(registry: MetricRegistry) -> None:
    names = registry.list_metrics()
    assert "test_metric" in names


def test_registry_validates_value(registry: MetricRegistry) -> None:
    metric = registry.get("test_metric")
    assert metric is not None
    assert metric.is_in_range(50.0) is True
    assert metric.is_in_range(150.0) is False
    assert metric.is_in_range(-1.0) is False
