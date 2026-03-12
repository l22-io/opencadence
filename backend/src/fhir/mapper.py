from datetime import datetime
from typing import Any
from uuid import UUID

from src.core.registry import MetricDefinition


def to_fhir_observation(
    device_id: UUID,
    metric_def: MetricDefinition,
    value: float,
    unit: str,
    timestamp: datetime,
) -> dict[str, Any]:
    """Map a raw sample to a FHIR R4 Observation resource."""
    return {
        "resourceType": "Observation",
        "status": "final",
        "code": {
            "coding": [
                {
                    "system": metric_def.fhir.system,
                    "code": metric_def.fhir.code,
                    "display": metric_def.fhir.display,
                }
            ],
            "text": metric_def.label,
        },
        "device": {"reference": f"Device/{device_id}"},
        "effectiveDateTime": timestamp.isoformat(),
        "valueQuantity": {
            "value": value,
            "unit": unit,
            "system": "http://unitsofmeasure.org",
        },
    }
