import time
from typing import Any

from .database import Database, ReplayDetected
from .rules import evaluate
from .schemas import TelemetryEnvelope
from .security import verify_signature


class UnknownDevice(Exception):
    pass


class InvalidSignature(Exception):
    pass


class StaleTimestamp(Exception):
    pass


class TelemetryService:
    def __init__(self, database: Database, max_clock_skew_seconds: int):
        self.database = database
        self.max_clock_skew_seconds = max_clock_skew_seconds

    def ingest(self, raw: dict[str, Any]) -> dict[str, Any]:
        envelope = TelemetryEnvelope.model_validate(raw)
        secret = self.database.get_device_secret(envelope.device_id)
        if secret is None:
            raise UnknownDevice(envelope.device_id)
        if not verify_signature(raw, secret):
            raise InvalidSignature(envelope.device_id)
        if abs(int(time.time()) - envelope.timestamp) > self.max_clock_skew_seconds:
            raise StaleTimestamp("device clock is outside the accepted window")

        result = self.database.insert_telemetry(envelope, evaluate(envelope.metrics))
        return {
            "accepted": True,
            "telemetry_id": result["telemetry_id"],
            "alerts": result["alerts"],
            "event": {
                "type": "telemetry",
                "device_id": envelope.device_id,
                "telemetry_id": result["telemetry_id"],
                "timestamp": envelope.timestamp,
                "sequence": envelope.sequence,
                "metrics": envelope.metrics.model_dump(),
                "alerts": result["alerts"],
            },
        }


__all__ = [
    "InvalidSignature",
    "ReplayDetected",
    "StaleTimestamp",
    "TelemetryService",
    "UnknownDevice",
]
