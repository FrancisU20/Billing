from __future__ import annotations

"""
Secrets Manager client with bounded in-memory cache (configurable TTL).

The secret is fetched ONCE per Lambda container and cached.
After the TTL it is refreshed automatically on the next call.

Usage:
    from shared.secrets.client import get_secret, get_secret_json
    api_key = get_secret("codelabs-billing/dev/email/brevo")
    creds   = get_secret_json("codelabs-billing/dev/db/master")
"""
import json
from collections import OrderedDict
from datetime import UTC, datetime, timedelta

import boto3

from shared.logger import get_logger

_log = get_logger(__name__)
_DEFAULT_MAX_CACHE_ENTRIES = 32
_cache: OrderedDict[str, tuple[str, datetime]] = OrderedDict()
_client = boto3.client("secretsmanager")


def _remember_secret(name: str, value: str, fetched_at: datetime, max_cache_entries: int) -> None:
    if max_cache_entries < 1:
        return

    _cache[name] = (value, fetched_at)
    _cache.move_to_end(name)
    while len(_cache) > max_cache_entries:
        _cache.popitem(last=False)


def get_secret(
    name: str,
    ttl_minutes: int = 5,
    *,
    max_cache_entries: int = _DEFAULT_MAX_CACHE_ENTRIES,
) -> str:
    if name in _cache:
        value, fetched_at = _cache[name]
        if datetime.now(UTC) - fetched_at < timedelta(minutes=ttl_minutes):
            _cache.move_to_end(name)
            return value

    _log.info("fetching secret from Secrets Manager", name=name)
    resp = _client.get_secret_value(SecretId=name)
    value = resp["SecretString"]
    _remember_secret(name, value, datetime.now(UTC), max_cache_entries)
    return value


def get_secret_json(
    name: str,
    ttl_minutes: int = 5,
    *,
    max_cache_entries: int = _DEFAULT_MAX_CACHE_ENTRIES,
) -> dict:
    return json.loads(get_secret(name, ttl_minutes, max_cache_entries=max_cache_entries))
