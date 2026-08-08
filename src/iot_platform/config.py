import os
from dataclasses import dataclass


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    database_path: str = "data/iot.db"
    device_id: str = "lab-esp32-01"
    device_secret: str = "demo-secret-change-me"
    mqtt_enabled: bool = False
    mqtt_host: str = "localhost"
    mqtt_port: int = 1883
    mqtt_topic: str = "campus/devices/+/telemetry"
    max_clock_skew_seconds: int = 300

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_path=os.getenv("IOT_DATABASE_PATH", "data/iot.db"),
            device_id=os.getenv("IOT_DEVICE_ID", "lab-esp32-01"),
            device_secret=os.getenv("IOT_DEVICE_SECRET", "demo-secret-change-me"),
            mqtt_enabled=_as_bool(os.getenv("IOT_MQTT_ENABLED", "false")),
            mqtt_host=os.getenv("IOT_MQTT_HOST", "localhost"),
            mqtt_port=int(os.getenv("IOT_MQTT_PORT", "1883")),
            mqtt_topic=os.getenv("IOT_MQTT_TOPIC", "campus/devices/+/telemetry"),
            max_clock_skew_seconds=int(os.getenv("IOT_MAX_CLOCK_SKEW_SECONDS", "300")),
        )
