from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request

from lambdas.subscriptions.domain.repositories.i_paypal_client import (
    IPayPalClient,
    PayPalCaptureResult,
    PayPalOrderResult,
)
from shared.logger import get_logger

_log = get_logger(__name__)

# Token cached at module level — Lambda warm reuse.
# Keyed by (base_url, client_id) to avoid cross-credential collisions in tests.
_token_cache: dict[tuple[str, str], dict] = {}


def _get_access_token(base_url: str, client_id: str, secret: str) -> str:
    now = time.time()
    cache_key = (base_url, client_id)
    cached = _token_cache.get(cache_key, {})
    if cached.get("token") and now < cached.get("expires_at", 0) - 60:
        return cached["token"]

    encoded = base64.b64encode(f"{client_id}:{secret}".encode()).decode()
    req = urllib.request.Request(  # noqa: S310
        f"{base_url}/v1/oauth2/token",
        data=b"grant_type=client_credentials",
        headers={
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
        body = json.loads(resp.read())

    token = body["access_token"]
    expires_in = int(body.get("expires_in", 32400))
    _token_cache[cache_key] = {"token": token, "expires_at": now + expires_in}
    return token


class PayPalClient(IPayPalClient):
    def __init__(
        self,
        base_url: str,
        client_id: str,
        secret: str,
        return_url: str,
        cancel_url: str,
    ) -> None:
        self._base_url = base_url
        self._client_id = client_id
        self._secret = secret
        self._return_url = return_url
        self._cancel_url = cancel_url

    def _token(self) -> str:
        return _get_access_token(self._base_url, self._client_id, self._secret)

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        # Always send a body (even empty {}) so PayPal receives correct Content-Length.
        data = json.dumps(body if body is not None else {}).encode()
        req = urllib.request.Request(  # noqa: S310
            f"{self._base_url}{path}",
            data=data,
            headers={
                "Authorization": f"Bearer {self._token()}",
                "Content-Type": "application/json",
            },
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode()
            _log.error("PayPal API error", status=exc.code, path=path, body=error_body)
            raise
        except urllib.error.URLError as exc:
            _log.error("PayPal network error", path=path, reason=str(exc.reason))
            raise

    def create_order(self, amount: str, currency: str) -> PayPalOrderResult:
        body = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "amount": {
                        "currency_code": currency,
                        "value": amount,
                    }
                }
            ],
            "application_context": {
                "return_url": self._return_url,
                "cancel_url": self._cancel_url,
                "user_action": "PAY_NOW",
            },
        }
        resp = self._request("POST", "/v2/checkout/orders", body)
        return PayPalOrderResult(order_id=resp["id"])

    def capture_order(self, order_id: str) -> PayPalCaptureResult:
        resp = self._request("POST", f"/v2/checkout/orders/{order_id}/capture")
        payer = resp.get("payer", {})
        payer_id = payer.get("payer_id", "")
        payer_email = payer.get("email_address")
        return PayPalCaptureResult(
            order_id=resp["id"],
            status=resp.get("status", ""),
            payer_id=payer_id,
            payer_email=payer_email,
        )
