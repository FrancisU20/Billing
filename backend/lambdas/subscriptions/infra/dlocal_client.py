from __future__ import annotations

import json
import urllib.error
import urllib.request
from decimal import ROUND_HALF_UP, Decimal

from lambdas.subscriptions.domain.repositories.i_dlocal_client import (
    DLocalConfirmPaymentResult,
    DLocalCreatePaymentResult,
    DLocalDirectChargeResult,
    DLocalRefundResult,
    IDLocalClient,
)
from shared.config import env
from shared.logger import get_logger
from shared.secrets.client import get_secret_json

_log = get_logger(__name__)

_USER_AGENT = "WaliBilling/1.0"
_CENT = Decimal("0.01")


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
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": _USER_AGENT,
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
                "amount": _json_amount(amount),
                "currency": currency,
                "country": country,
                "allow_transparent": True,
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
        client_first_name: str,
        client_last_name: str,
        client_email: str,
        client_document_type: str,
        client_document: str,
    ) -> DLocalConfirmPaymentResult:
        body = {
            "cardToken": card_token,
            "clientFirstName": client_first_name,
            "clientLastName": client_last_name,
            "clientEmail": client_email,
            "clientDocumentType": client_document_type,
            "clientDocument": client_document,
        }
        resp = self._request("POST", f"/v1/payments/confirm/{checkout_token}", body)
        payer = resp.get("payer", {})
        redirect_url = resp.get("redirect_url")
        status = resp.get("status")
        if not status and resp.get("success") is True:
            status = "PENDING" if redirect_url else "PAID"
        return DLocalConfirmPaymentResult(
            payment_id=resp.get("id") or resp.get("payment_id") or "",
            status=status or "",
            payer_id=payer.get("id"),
            payer_email=payer.get("email"),
            redirect_url=redirect_url,
        )

    def refund_payment(self, order_id: str, amount: str, currency: str) -> DLocalRefundResult:
        resp = self._request(
            "POST",
            f"/v1/payments/{order_id}/refund",
            {"amount": _json_amount(amount), "currency": currency},
        )
        return DLocalRefundResult(
            refund_id=resp.get("id") or "",
            status=resp.get("status") or "REFUNDED",
        )

    def charge_saved_payer(
        self, payer_id: str, amount: str, currency: str, country: str
    ) -> DLocalDirectChargeResult:
        resp = self._request(
            "POST",
            "/v1/payments",
            {
                "amount": _json_amount(amount),
                "currency": currency,
                "country": country,
                "payer": {"id": payer_id},
            },
        )
        return DLocalDirectChargeResult(
            payment_id=resp.get("id") or "",
            status=resp.get("status") or "REJECTED",
        )


def _json_amount(amount: str) -> float:
    """dLocal Go requires JSON numbers; quantize explicitly before leaving Decimal land."""
    return float(Decimal(amount).quantize(_CENT, ROUND_HALF_UP))


def make_dlocal_client() -> DLocalClient:
    """Builds a DLocalClient from environment variables and Secrets Manager."""
    creds = get_secret_json(env("DLOCALGO_CREDENTIALS_NAME"))
    return DLocalClient(
        base_url=env("DLOCALGO_API_URL"),
        api_key=creds["api_key"],
        secret_key=creds["secret_key"],
    )
