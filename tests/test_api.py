import time

from fastapi.testclient import TestClient

from iot_platform.config import Settings
from iot_platform.main import create_app
from iot_platform.security import sign_payload

SECRET = "test-secret"


def payload(sequence=1, temperature=24):
    value = {
        "device_id": "test-node",
        "timestamp": int(time.time()),
        "sequence": sequence,
        "metrics": {
            "temperature": temperature,
            "humidity": 45,
            "air_quality": 60,
            "battery": 80,
            "rssi": -55,
        },
    }
    value["signature"] = sign_payload(value, SECRET)
    return value


def app_for(tmp_path):
    return create_app(
        Settings(
            database_path=str(tmp_path / "test.db"),
            device_id="test-node",
            device_secret=SECRET,
            mqtt_enabled=False,
        )
    )


def test_ingest_and_query_history(tmp_path):
    with TestClient(app_for(tmp_path)) as client:
        response = client.post("/api/v1/telemetry", json=payload())
        assert response.status_code == 202
        assert response.json()["alerts"] == []

        history = client.get("/api/v1/telemetry/history?device_id=test-node").json()
        assert len(history) == 1
        assert history[0]["temperature"] == 24


def test_history_is_chronological_when_samples_share_a_timestamp(tmp_path):
    with TestClient(app_for(tmp_path)) as client:
        client.post("/api/v1/telemetry", json=payload(sequence=10))
        client.post("/api/v1/telemetry", json=payload(sequence=11))
        history = client.get("/api/v1/telemetry/history?device_id=test-node").json()
        assert [row["sequence"] for row in history] == [10, 11]


def test_alert_replay_and_invalid_signature(tmp_path):
    with TestClient(app_for(tmp_path)) as client:
        hot = payload(sequence=7, temperature=36)
        response = client.post("/api/v1/telemetry", json=hot)
        assert response.status_code == 202
        assert response.json()["alerts"][0]["severity"] == "critical"

        assert client.post("/api/v1/telemetry", json=hot).status_code == 409

        bad = payload(sequence=8)
        bad["signature"] = "0" * 64
        assert client.post("/api/v1/telemetry", json=bad).status_code == 401
