import argparse
import json
import math
import os
import random
import time
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .security import sign_payload


def metrics_for(sequence: int, scenario: str) -> dict[str, Any]:
    wave = math.sin(sequence / 8)
    temperature = 24 + wave * 2 + random.uniform(-0.3, 0.3)
    air_quality = int(55 + wave * 12 + random.uniform(-4, 4))
    battery = max(5, 98 - sequence * 0.03)
    if scenario == "heatwave":
        temperature += min(14, sequence * 0.45)
    elif scenario == "unstable" and sequence % 12 >= 8:
        air_quality += 145
    return {
        "temperature": round(temperature, 2),
        "humidity": round(48 - wave * 5 + random.uniform(-1, 1), 2),
        "air_quality": air_quality,
        "battery": round(battery, 2),
        "rssi": random.randint(-72, -48),
    }


def build_payload(
    device_id: str,
    secret: str,
    sequence: int,
    scenario: str,
    sample_index: int = 0,
):
    payload = {
        "device_id": device_id,
        "timestamp": int(time.time()),
        "sequence": sequence,
        "metrics": metrics_for(sample_index, scenario),
    }
    payload["signature"] = sign_payload(payload, secret)
    return payload


def send_http(url: str, payload: dict[str, Any]) -> None:
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=5) as response:
            response.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="Signed IoT device simulator")
    parser.add_argument("--transport", choices=["http", "mqtt"], default="http")
    parser.add_argument("--api-url", default="http://localhost:8000/api/v1/telemetry")
    parser.add_argument("--mqtt-host", default="localhost")
    parser.add_argument("--mqtt-port", type=int, default=1883)
    parser.add_argument("--interval", type=float, default=2)
    parser.add_argument("--count", type=int, default=0, help="0 means keep running")
    parser.add_argument("--scenario", choices=["normal", "heatwave", "unstable"], default="normal")
    parser.add_argument("--device-id", default=os.getenv("IOT_DEVICE_ID", "lab-esp32-01"))
    parser.add_argument("--secret", default=os.getenv("IOT_DEVICE_SECRET", "demo-secret-change-me"))
    args = parser.parse_args()

    mqtt_client = None
    if args.transport == "mqtt":
        import paho.mqtt.client as mqtt

        mqtt_client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2, client_id=f"sim-{args.device_id}"
        )
        mqtt_client.connect(args.mqtt_host, args.mqtt_port, 30)
        mqtt_client.loop_start()

    sequence = int(time.time() * 1000)
    sent = 0
    print(f"模拟设备 {args.device_id} 已启动，场景：{args.scenario}")
    try:
        while args.count == 0 or sent < args.count:
            payload = build_payload(args.device_id, args.secret, sequence, args.scenario, sent)
            if mqtt_client:
                topic = f"campus/devices/{args.device_id}/telemetry"
                info = mqtt_client.publish(topic, json.dumps(payload), qos=1)
                info.wait_for_publish(timeout=5)
            else:
                send_http(args.api_url, payload)
            print(
                f"seq={sequence} temp={payload['metrics']['temperature']}°C "
                f"aqi={payload['metrics']['air_quality']}"
            )
            sequence += 1
            sent += 1
            if args.count == 0 or sent < args.count:
                time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n模拟设备已停止")
    finally:
        if mqtt_client:
            mqtt_client.disconnect()
            mqtt_client.loop_stop()


if __name__ == "__main__":
    main()
