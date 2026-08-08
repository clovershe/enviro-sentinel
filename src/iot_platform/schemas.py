from typing import Literal

from pydantic import BaseModel, Field


class Metrics(BaseModel):
    temperature: float = Field(ge=-40, le=125)
    humidity: float = Field(ge=0, le=100)
    air_quality: int = Field(ge=0, le=500)
    battery: float = Field(ge=0, le=100)
    rssi: int = Field(ge=-120, le=0)


class TelemetryEnvelope(BaseModel):
    device_id: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    timestamp: int = Field(gt=0)
    sequence: int = Field(ge=0)
    metrics: Metrics
    signature: str = Field(min_length=64, max_length=64)


class AlertView(BaseModel):
    id: int
    code: str
    severity: Literal["warning", "critical"]
    message: str
    acknowledged: bool = False


class IngestResult(BaseModel):
    accepted: bool = True
    telemetry_id: int
    alerts: list[AlertView]
