from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class Sample(BaseModel):
    """A single health data sample from a wearable device."""

    metric: str
    value: float
    unit: str
    timestamp: datetime
    source: str


class IngestPayload(BaseModel):
    """Batch payload for health data ingestion."""

    device_id: UUID
    batch: list[Sample] = Field(min_length=1, max_length=1000)
