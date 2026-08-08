from iot_platform.rules import evaluate
from iot_platform.schemas import Metrics


def metric(**overrides):
    values = dict(temperature=24, humidity=50, air_quality=50, battery=90, rssi=-60)
    values.update(overrides)
    return Metrics(**values)


def test_normal_metrics_have_no_alerts():
    assert evaluate(metric()) == []


def test_critical_temperature_and_low_battery_are_detected():
    alerts = evaluate(metric(temperature=36, battery=10))
    assert [(alert.code, alert.severity) for alert in alerts] == [
        ("HIGH_TEMPERATURE", "critical"),
        ("LOW_BATTERY", "warning"),
    ]
