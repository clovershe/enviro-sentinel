import asyncio
import json
import logging

import paho.mqtt.client as mqtt

from .realtime import ConnectionManager
from .service import TelemetryService

logger = logging.getLogger(__name__)


class MqttBridge:
    def __init__(
        self,
        host: str,
        port: int,
        topic: str,
        service: TelemetryService,
        realtime: ConnectionManager,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        self.host = host
        self.port = port
        self.topic = topic
        self.service = service
        self.realtime = realtime
        self.loop = loop
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="iot-api")
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect

    def start(self) -> None:
        logger.info("Connecting to MQTT broker at %s:%s", self.host, self.port)
        self.client.connect_async(self.host, self.port, keepalive=30)
        self.client.loop_start()

    def stop(self) -> None:
        self.client.disconnect()
        self.client.loop_stop()

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        if reason_code == 0:
            client.subscribe(self.topic, qos=1)
            logger.info("Subscribed to MQTT topic %s", self.topic)
        else:
            logger.error("MQTT connection failed: %s", reason_code)

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties) -> None:
        if reason_code != 0:
            logger.warning("Unexpected MQTT disconnect: %s", reason_code)

    def _on_message(self, client, userdata, message) -> None:
        try:
            raw = json.loads(message.payload.decode("utf-8"))
            result = self.service.ingest(raw)
            asyncio.run_coroutine_threadsafe(self.realtime.broadcast(result["event"]), self.loop)
        except Exception as exc:
            logger.warning("Rejected MQTT message on %s: %s", message.topic, exc)
