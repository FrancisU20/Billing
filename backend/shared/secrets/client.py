"""
Cliente de Secrets Manager con cache en memoria (TTL configurable).

El secreto se obtiene UNA vez por contenedor Lambda y se cachea.
Pasado el TTL se refresca automáticamente en la siguiente llamada.

Uso:
    from shared.secrets.client import get_secret, get_secret_json
    api_key = get_secret("codelabs-billing/dev/email/brevo")
    creds   = get_secret_json("codelabs-billing/dev/db/master")
"""
import json
from datetime import datetime, timedelta, timezone

import boto3

from shared.logger import get_logger

_log    = get_logger(__name__)
_cache: dict[str, tuple[str, datetime]] = {}
_client = boto3.client("secretsmanager")


def get_secret(name: str, ttl_minutes: int = 5) -> str:
    if name in _cache:
        value, fetched_at = _cache[name]
        if datetime.now(timezone.utc) - fetched_at < timedelta(minutes=ttl_minutes):
            return value

    _log.info("obteniendo secreto de Secrets Manager", name=name)
    resp  = _client.get_secret_value(SecretId=name)
    value = resp["SecretString"]
    _cache[name] = (value, datetime.now(timezone.utc))
    return value


def get_secret_json(name: str, ttl_minutes: int = 5) -> dict:
    return json.loads(get_secret(name, ttl_minutes))
