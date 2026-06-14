from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RequestOnboardingOtpCommand:
    ruc: str
    trade_name: str
    legal_name: str
    legal_rep_name: str
    email: str
    phone: str
    address: str
    accounting_required: bool
    plan_id: str
    certificate_b64: str | None = None
    cert_password: str | None = None


@dataclass(frozen=True)
class ConfirmOnboardingOtpCommand:
    verification_id: str
    otp: str
    ruc: str
    trade_name: str
    legal_name: str
    legal_rep_name: str
    email: str
    phone: str
    address: str
    accounting_required: bool
    plan_id: str
    certificate_b64: str | None = None
    cert_password: str | None = None
