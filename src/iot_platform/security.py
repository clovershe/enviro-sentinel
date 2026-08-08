import hashlib
import hmac
import json
from typing import Any


def canonical_bytes(payload: dict[str, Any]) -> bytes:
    unsigned = {key: value for key, value in payload.items() if key != "signature"}
    return json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def sign_payload(payload: dict[str, Any], secret: str) -> str:
    return hmac.new(secret.encode("utf-8"), canonical_bytes(payload), hashlib.sha256).hexdigest()


def verify_signature(payload: dict[str, Any], secret: str) -> bool:
    supplied = str(payload.get("signature", ""))
    expected = sign_payload(payload, secret)
    return hmac.compare_digest(supplied, expected)
