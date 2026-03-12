from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AggregatedSample(BaseModel):
    time: datetime
    min: float | None = None
    max: float | None = None
    mean: float | None = None
    stddev: float | None = None
    count: int | None = None


class RawSample(BaseModel):
    time: datetime
    value: float
    unit: str
    source: str


class DataQueryResponse(BaseModel):
    device_id: UUID
    metric: str
    resolution: str
    samples: list[AggregatedSample] | list[RawSample]


class DeviceResponse(BaseModel):
    id: UUID
    name: str
    source_type: str
    created_at: datetime
    active: bool


class AnomalyResponse(BaseModel):
    time: datetime
    device_id: UUID
    metric: str
    value: float
    reason: str
    severity: str
    context: dict | None = None
