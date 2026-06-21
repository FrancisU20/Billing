from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from lambdas.subscriptions.infra.dlocal_client import DLocalClient


class _FakeResponse:
    def __init__(self, payload: dict | None = None) -> None:
        self._payload = payload or {
            "id": "DP-123",
            "merchant_checkout_token": "mct_123",
        }

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode()


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
        self.assertEqual(captured["request"].get_header("User-agent"), "WaliBilling/1.0")
        self.assertNotIn("payment_method_id", body)
        self.assertNotIn("payment_method_flow", body)

    def test_confirm_payment_accepts_sample_success_response(self) -> None:
        captured = {}

        def fake_urlopen(req, timeout):
            captured["request"] = req
            captured["timeout"] = timeout
            return _FakeResponse(
                {
                    "success": True,
                    "payment_id": "DP-123",
                    "payer": {
                        "id": "payer-123",
                        "email": "buyer@example.com",
                    },
                }
            )

        client = DLocalClient(
            base_url="https://api-sbx.dlocalgo.com",
            api_key="api-key",
            secret_key="secret-key",
        )

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = client.confirm_payment(
                checkout_token="mct_123",
                card_token="card_tok",
                client_first_name="Test",
                client_last_name="User",
                client_email="buyer@example.com",
                client_document_type="CI",
                client_document="1712345678",
            )

        body = json.loads(captured["request"].data.decode())
        self.assertEqual(result.payment_id, "DP-123")
        self.assertEqual(result.status, "PAID")
        self.assertEqual(result.payer_id, "payer-123")
        self.assertEqual(result.payer_email, "buyer@example.com")
        self.assertEqual(body["cardToken"], "card_tok")
        self.assertEqual(body["clientFirstName"], "Test")
        self.assertNotIn("country", body)
        self.assertEqual(
            captured["request"].full_url,
            "https://api-sbx.dlocalgo.com/v1/payments/confirm/mct_123",
        )

    def test_confirm_payment_maps_redirect_response_to_pending(self) -> None:
        def fake_urlopen(req, timeout):
            return _FakeResponse(
                {
                    "success": True,
                    "payment_id": "DP-123",
                    "redirect_url": "https://3ds.example.test/auth",
                }
            )

        client = DLocalClient(
            base_url="https://api-sbx.dlocalgo.com",
            api_key="api-key",
            secret_key="secret-key",
        )

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = client.confirm_payment(
                checkout_token="mct_123",
                card_token="card_tok",
                client_first_name="Test",
                client_last_name="User",
                client_email="buyer@example.com",
                client_document_type="CI",
                client_document="1712345678",
            )

        self.assertEqual(result.payment_id, "DP-123")
        self.assertEqual(result.status, "PENDING")
        self.assertEqual(result.redirect_url, "https://3ds.example.test/auth")


if __name__ == "__main__":
    unittest.main()
