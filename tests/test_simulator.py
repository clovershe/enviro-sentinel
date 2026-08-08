from iot_platform.security import verify_signature
from iot_platform.simulator import build_payload, metrics_for


def test_first_sample_starts_with_realistic_battery_and_valid_signature():
    payload = build_payload("test-node", "secret", 123456, "normal", sample_index=0)
    assert payload["metrics"]["battery"] == 98
    assert verify_signature(payload, "secret")


def test_heatwave_ramps_up_instead_of_starting_at_maximum():
    first = metrics_for(0, "heatwave")
    later = metrics_for(40, "heatwave")
    assert first["temperature"] < 30
    assert later["temperature"] > 35
