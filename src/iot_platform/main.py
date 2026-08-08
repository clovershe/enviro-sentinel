import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

from fastapi import Body, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from .config import Settings
from .database import Database, ReplayDetected
from .mqtt_bridge import MqttBridge
from .realtime import ConnectionManager
from .schemas import IngestResult
from .service import InvalidSignature, StaleTimestamp, TelemetryService, UnknownDevice


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    config = settings or Settings.from_env()
    database = Database(config.database_path)
    realtime = ConnectionManager()
    service = TelemetryService(database, config.max_clock_skew_seconds)
    mqtt_bridge: Optional[MqttBridge] = None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        nonlocal mqtt_bridge
        database.initialize()
        database.register_device(config.device_id, "实验室环境节点 01", config.device_secret)
        if config.mqtt_enabled:
            mqtt_bridge = MqttBridge(
                config.mqtt_host,
                config.mqtt_port,
                config.mqtt_topic,
                service,
                realtime,
                asyncio.get_running_loop(),
            )
            mqtt_bridge.start()
        yield
        if mqtt_bridge:
            mqtt_bridge.stop()

    app = FastAPI(
        title="Northwest IoT Observatory API",
        version="0.1.0",
        description="Secure telemetry ingestion, rules, storage, and live updates.",
        lifespan=lifespan,
    )
    app.state.database = database

    @app.get("/api/v1/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "mqtt_enabled": config.mqtt_enabled}

    @app.post("/api/v1/telemetry", response_model=IngestResult, status_code=202)
    async def ingest(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
        try:
            result = service.ingest(payload)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc
        except UnknownDevice as exc:
            raise HTTPException(status_code=404, detail="unknown device") from exc
        except InvalidSignature as exc:
            raise HTTPException(status_code=401, detail="invalid signature") from exc
        except StaleTimestamp as exc:
            raise HTTPException(status_code=408, detail=str(exc)) from exc
        except ReplayDetected as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        await realtime.broadcast(result["event"])
        return result

    @app.get("/api/v1/devices")
    def list_devices():
        return database.devices()

    @app.get("/api/v1/telemetry/history")
    def history(
        device_id: str = Query(default=config.device_id),
        limit: int = Query(default=60, ge=1, le=500),
    ):
        return database.history(device_id, limit)

    @app.get("/api/v1/alerts")
    def alerts(
        device_id: Optional[str] = None,
        limit: int = Query(default=20, ge=1, le=200),
    ):
        return database.alerts(device_id, limit)

    @app.post("/api/v1/alerts/{alert_id}/acknowledge")
    def acknowledge(alert_id: int):
        if not database.acknowledge_alert(alert_id):
            raise HTTPException(status_code=404, detail="alert not found")
        return {"acknowledged": True, "alert_id": alert_id}

    @app.websocket("/ws/telemetry")
    async def telemetry_socket(websocket: WebSocket):
        await realtime.connect(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            realtime.disconnect(websocket)

    web_dir = Path(__file__).parent / "web"
    app.mount("/assets", StaticFiles(directory=web_dir), name="assets")

    @app.get("/", include_in_schema=False)
    def dashboard():
        return FileResponse(web_dir / "index.html")

    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("iot_platform.main:app", host="0.0.0.0", port=8000, reload=False)
