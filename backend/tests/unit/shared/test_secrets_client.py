from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from shared.secrets import client as secrets_client


class FakeSecretsManagerClient:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}
        self.calls: list[str] = []

    def get_secret_value(self, **kwargs) -> dict:
        secret_id = kwargs["SecretId"]
        self.calls.append(secret_id)
        return {"SecretString": self.values[secret_id]}


class SecretsClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fake_client = FakeSecretsManagerClient()
        self.original_client = secrets_client._client
        secrets_client._client = self.fake_client
        secrets_client._cache.clear()

    def tearDown(self) -> None:
        secrets_client._client = self.original_client
        secrets_client._cache.clear()

    def test_get_secret_uses_cache_before_ttl_expires(self) -> None:
        self.fake_client.values["secret-a"] = "first"

        first = secrets_client.get_secret("secret-a")
        self.fake_client.values["secret-a"] = "second"
        second = secrets_client.get_secret("secret-a")

        self.assertEqual(first, "first")
        self.assertEqual(second, "first")
        self.assertEqual(self.fake_client.calls, ["secret-a"])

    def test_get_secret_refetches_after_ttl_expires(self) -> None:
        self.fake_client.values["secret-a"] = "new"
        secrets_client._cache["secret-a"] = (
            "old",
            datetime.now(UTC) - timedelta(minutes=10),
        )

        value = secrets_client.get_secret("secret-a", ttl_minutes=5)

        self.assertEqual(value, "new")
        self.assertEqual(self.fake_client.calls, ["secret-a"])

    def test_get_secret_evicts_least_recently_used_entry(self) -> None:
        self.fake_client.values.update(
            {
                "secret-a": "a",
                "secret-b": "b",
                "secret-c": "c",
            }
        )

        secrets_client.get_secret("secret-a", max_cache_entries=2)
        secrets_client.get_secret("secret-b", max_cache_entries=2)
        secrets_client.get_secret("secret-a", max_cache_entries=2)
        secrets_client.get_secret("secret-c", max_cache_entries=2)

        self.assertEqual(list(secrets_client._cache), ["secret-a", "secret-c"])

    def test_get_secret_can_disable_cache(self) -> None:
        self.fake_client.values["secret-a"] = "first"

        secrets_client.get_secret("secret-a", max_cache_entries=0)
        self.fake_client.values["secret-a"] = "second"
        value = secrets_client.get_secret("secret-a", max_cache_entries=0)

        self.assertEqual(value, "second")
        self.assertEqual(self.fake_client.calls, ["secret-a", "secret-a"])

    def test_get_secret_json_uses_secret_string(self) -> None:
        self.fake_client.values["json-secret"] = '{"api_key": "abc"}'

        value = secrets_client.get_secret_json("json-secret")

        self.assertEqual(value, {"api_key": "abc"})


if __name__ == "__main__":
    unittest.main()
