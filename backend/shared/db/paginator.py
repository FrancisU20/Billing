from __future__ import annotations

"""
DynamoDB pagination with an opaque cursor (base64 of LastEvaluatedKey).

The client receives and sends `next_token` as an opaque string.
Internally the DynamoDB LastEvaluatedKey is encoded/decoded.
"""

import base64
import json

from shared.errors import ValidationError


def encode_cursor(last_evaluated_key: dict | None) -> str | None:
    if not last_evaluated_key:
        return None
    return base64.b64encode(json.dumps(last_evaluated_key, default=str).encode()).decode()


def decode_cursor(next_token: str | None) -> dict | None:
    if not next_token:
        return None
    try:
        return json.loads(base64.b64decode(next_token.encode()).decode())
    except Exception as exc:
        raise ValidationError("next_token inválido") from exc
