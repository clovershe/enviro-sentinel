from iot_platform.security import sign_payload, verify_signature


def test_signature_is_stable_and_detects_tampering():
    payload = {"device_id": "node-1", "timestamp": 1, "metrics": {"temperature": 20}}
    payload["signature"] = sign_payload(payload, "secret")
    assert verify_signature(payload, "secret")

    payload["metrics"]["temperature"] = 99
    assert not verify_signature(payload, "secret")
