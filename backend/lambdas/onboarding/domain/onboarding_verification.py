from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import uuid4

from lambdas.onboarding.domain.errors import (
    OnboardingOtpAttemptsExceededError,
    OnboardingOtpExpiredError,
    OnboardingOtpInvalidError,
)
from shared.dates import now_utc

OTP_TTL_MINUTES = 10
OTP_MAX_ATTEMPTS = 5
OTP_DIGITS = 6
_HASH_ITERATIONS = 100_000


def _now() -> datetime:
    return now_utc()


def generate_otp() -> str:
    return f"{secrets.randbelow(10**OTP_DIGITS):0{OTP_DIGITS}d}"


def _hash_otp(otp: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        otp.encode("utf-8"),
        bytes.fromhex(salt),
        _HASH_ITERATIONS,
    ).hex()


@dataclass
class OnboardingVerification:
    ruc: str
    email: str
    plan_id: str
    payload_hash: str
    otp_hash: str
    otp_salt: str
    self_service: bool
    id: str = field(default_factory=lambda: str(uuid4()))
    attempts: int = 0
    max_attempts: int = OTP_MAX_ATTEMPTS
    expires_at: datetime = field(
        default_factory=lambda: _now() + timedelta(minutes=OTP_TTL_MINUTES)
    )
    used_at: datetime | None = None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    @classmethod
    def create(
        cls,
        *,
        ruc: str,
        email: str,
        plan_id: str,
        payload_hash: str,
        self_service: bool,
        otp: str,
    ) -> OnboardingVerification:
        salt = secrets.token_bytes(16).hex()
        return cls(
            ruc=ruc,
            email=email,
            plan_id=plan_id,
            payload_hash=payload_hash,
            otp_hash=_hash_otp(otp, salt),
            otp_salt=salt,
            self_service=self_service,
        )

    def ensure_active(self, now: datetime | None = None) -> None:
        current = now or _now()
        if self.used_at is not None:
            raise OnboardingOtpInvalidError()
        if current >= self.expires_at:
            raise OnboardingOtpExpiredError()
        if self.attempts >= self.max_attempts:
            raise OnboardingOtpAttemptsExceededError()

    def verify(self, otp: str) -> bool:
        """Compares the OTP against the stored hash. Does not check active state;
        call `ensure_active()` first."""
        return secrets.compare_digest(_hash_otp(otp, self.otp_salt), self.otp_hash)

    def register_failed_attempt(self) -> None:
        self.attempts += 1
        self.updated_at = _now()
        if self.attempts >= self.max_attempts:
            raise OnboardingOtpAttemptsExceededError()
        raise OnboardingOtpInvalidError()

    def mark_used(self) -> None:
        self.used_at = _now()
        self.updated_at = self.used_at

    @property
    def ttl(self) -> int:
        return int(self.expires_at.timestamp())
