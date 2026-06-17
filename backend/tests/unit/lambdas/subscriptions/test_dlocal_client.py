from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from lambdas.subscriptions.infra.dlocal_client import DLocalClient


class _FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(
            {
                "id": "DP-123",
                "merchant_checkout_token": "mct_123",
            }
        ).encode()


class DLocalClientTests(unittest.TestCase):
    def test_create_payment_enables_transparent_checkout(self) -> None:
        captured = {}

        def fake_urlopen(req, timeout):
            captured["request"] = req
            captured["timeout"] = timeout
            return _FakeResponse()

        client = DLocalClient(
            base_url="https://api-sbx.dlocalgo.com",
            api_key="api-key",
            secret_key="secret-key",
        )

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = client.create_payment("5.99", "USD", "EC")

        body = json.loads(captured["request"].data.decode())
        self.assertEqual(result.payment_id, "DP-123")
        self.assertEqual(result.checkout_token, "mct_123")
        self.assertTrue(body["allow_transparent"])
        self.assertEqual(
            captured["request"].get_header("Authorization"),
            "Bearer api-key:secret-key",
        )
        self.assertEqual(captured["request"].get_header("Accept"), "application/json")
        self.assertEqual(captured["request"].get_header("Content-type"), "application/json")
        self.assertEqual(captured["request"].get_header("User-agent"), "CodeLabsBillingCloud/1.0")
        self.assertNotIn("payment_method_id", body)
        self.assertNotIn("payment_method_flow", body)


if __name__ == "__main__":
    unittest.main()
