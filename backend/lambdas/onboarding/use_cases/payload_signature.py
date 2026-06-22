from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, is_dataclass
from typing import Any

_IGNORED_FIELDS = {"otp", "verification_id", "order_id"}


def onboarding_payload_hash(payload: Any) -> str:
    if is_dataclass(payload):
        raw = asdict(payload)
    elif hasattr(payload, "model_dump"):
        raw = payload.model_dump()
    else:
        raw = dict(payload)

    canonical = {
        key: _normalize(value)
        for key, value in raw.items()
        if key not in _IGNORED_FIELDS and value is not None
    }
    serialized = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _normalize(value):
    if isinstance(value, str):
        return value.strip()
    return value
