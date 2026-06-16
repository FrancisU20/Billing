from __future__ import annotations

import json
import urllib.error
import urllib.request

from lambdas.subscriptions.domain.repositories.i_dlocal_client import (
    DLocalConfirmPaymentResult,
    DLocalCreatePaymentResult,
    IDLocalClient,
)
from shared.logger import get_logger

_log = get_logger(__name__)


class DLocalClient(IDLocalClient):
    def __init__(self, base_url: str, api_key: str, secret_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._auth = f"{api_key}:{secret_key}"

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        data = json.dumps(body or {}).encode()
        req = urllib.request.Request(  # noqa: S310
            f"{self._base_url}{path}",
            data=data,
            headers={
                "Authorization": f"Bearer {self._auth}",
                "Content-Type": "application/json",
            },
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310  # nosec B310
                return json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode()
            _log.error("dLocal API error", status=exc.code, path=path, body=error_body)
            raise
        except urllib.error.URLError as exc:
            _log.error("dLocal network error", path=path, reason=str(exc.reason))
            raise

    def create_payment(self, amount: str, currency: str, country: str) -> DLocalCreatePaymentResult:
        resp = self._request(
            "POST",
            "/v1/payments",
            {
                "amount": amount,
                "currency": currency,
                "country": country,
                "payment_method_id": "CARD",
                "payment_method_flow": "TRANSPARENT",
            },
        )
        return DLocalCreatePaymentResult(
            payment_id=resp["id"],
            checkout_token=resp["merchant_checkout_token"],
        )

    def confirm_payment(
        self,
        checkout_token: str,
        card_token: str,
        payer_email: str | None,
    ) -> DLocalConfirmPaymentResult:
        body: dict = {"card": {"token": card_token}}
        if payer_email:
            body["payer"] = {"email": payer_email}
        resp = self._request("POST", f"/v1/payments/confirm/{checkout_token}", body)
        payer = resp.get("payer", {})
        return DLocalConfirmPaymentResult(
            payment_id=resp["id"],
            status=resp.get("status", ""),
            payer_id=payer.get("id"),
            payer_email=payer.get("email"),
        )
