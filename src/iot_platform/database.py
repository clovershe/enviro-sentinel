import sqlite3
import threading
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Optional

from .rules import RuleAlert
from .schemas import TelemetryEnvelope


class ReplayDetected(Exception):
    pass


class Database:
    def __init__(self, path: str):
        self.path = path
        self._write_lock = threading.Lock()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def initialize(self) -> None:
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS devices (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    secret TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL REFERENCES devices(id),
                    sequence INTEGER NOT NULL,
                    observed_at INTEGER NOT NULL,
                    received_at INTEGER NOT NULL,
                    temperature REAL NOT NULL,
                    humidity REAL NOT NULL,
                    air_quality INTEGER NOT NULL,
                    battery REAL NOT NULL,
                    rssi INTEGER NOT NULL,
                    UNIQUE(device_id, sequence)
                );
                CREATE INDEX IF NOT EXISTS idx_telemetry_device_time
                    ON telemetry(device_id, observed_at DESC);
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telemetry_id INTEGER NOT NULL REFERENCES telemetry(id),
                    device_id TEXT NOT NULL REFERENCES devices(id),
                    code TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    acknowledged INTEGER NOT NULL DEFAULT 0,
                    created_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_alerts_device_time
                    ON alerts(device_id, created_at DESC);
                """
            )

    def register_device(self, device_id: str, name: str, secret: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO devices(id, name, secret, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET name = excluded.name, secret = excluded.secret
                """,
                (device_id, name, secret, int(time.time())),
            )

    def get_device_secret(self, device_id: str) -> Optional[str]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT secret FROM devices WHERE id = ?", (device_id,)
            ).fetchone()
        return str(row["secret"]) if row else None

    def insert_telemetry(
        self, envelope: TelemetryEnvelope, alerts: Sequence[RuleAlert]
    ) -> dict[str, Any]:
        metrics = envelope.metrics
        now = int(time.time())
        with self._write_lock, self._connect() as connection:
            latest = connection.execute(
                "SELECT MAX(sequence) AS value FROM telemetry WHERE device_id = ?",
                (envelope.device_id,),
            ).fetchone()
            if latest and latest["value"] is not None and envelope.sequence <= latest["value"]:
                raise ReplayDetected("sequence must be greater than the last accepted value")

            cursor = connection.execute(
                """
                INSERT INTO telemetry(
                    device_id, sequence, observed_at, received_at,
                    temperature, humidity, air_quality, battery, rssi
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    envelope.device_id,
                    envelope.sequence,
                    envelope.timestamp,
                    now,
                    metrics.temperature,
                    metrics.humidity,
                    metrics.air_quality,
                    metrics.battery,
                    metrics.rssi,
                ),
            )
            telemetry_id = int(cursor.lastrowid)
            alert_rows = []
            for alert in alerts:
                alert_cursor = connection.execute(
                    """
                    INSERT INTO alerts(
                        telemetry_id, device_id, code, severity, message, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        telemetry_id,
                        envelope.device_id,
                        alert.code,
                        alert.severity,
                        alert.message,
                        now,
                    ),
                )
                alert_rows.append(
                    {
                        "id": int(alert_cursor.lastrowid),
                        "code": alert.code,
                        "severity": alert.severity,
                        "message": alert.message,
                        "acknowledged": False,
                    }
                )
        return {"telemetry_id": telemetry_id, "alerts": alert_rows}

    def devices(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT d.id, d.name, MAX(t.observed_at) AS last_seen
                FROM devices d LEFT JOIN telemetry t ON t.device_id = d.id
                GROUP BY d.id, d.name ORDER BY d.id
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def history(self, device_id: str, limit: int) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, device_id, sequence, observed_at, received_at,
                       temperature, humidity, air_quality, battery, rssi
                FROM telemetry WHERE device_id = ?
                ORDER BY observed_at DESC, id DESC LIMIT ?
                """,
                (device_id, limit),
            ).fetchall()
        return [dict(row) for row in reversed(rows)]

    def alerts(self, device_id: Optional[str], limit: int) -> list[dict[str, Any]]:
        query = """
            SELECT id, telemetry_id, device_id, code, severity, message,
                   acknowledged, created_at
            FROM alerts
        """
        params: list = []
        if device_id:
            query += " WHERE device_id = ?"
            params.append(device_id)
        query += " ORDER BY created_at DESC, id DESC LIMIT ?"
        params.append(limit)
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        result = [dict(row) for row in rows]
        for row in result:
            row["acknowledged"] = bool(row["acknowledged"])
        return result

    def acknowledge_alert(self, alert_id: int) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE alerts SET acknowledged = 1 WHERE id = ?", (alert_id,)
            )
        return cursor.rowcount == 1
