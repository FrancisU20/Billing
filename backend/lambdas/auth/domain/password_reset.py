from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from lambdas.auth.domain.errors import InvalidChallengeResponseError
from shared.dates import now_utc

PASSWORD_RESET_TTL_MINUTES = 15
PASSWORD_RESET_MAX_ATTEMPTS = 5
PASSWORD_RESET_DIGITS = 6
_HASH_ITERATIONS = 100_000


def _now() -> datetime:
    return now_utc()


def generate_reset_code() -> str:
    return f"{secrets.randbelow(10**PASSWORD_RESET_DIGITS):0{PASSWORD_RESET_DIGITS}d}"


def _hash_code(code: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        code.encode("utf-8"),
        bytes.fromhex(salt),
        _HASH_ITERATIONS,
    ).hex()


@dataclass
class PasswordReset:
    username: str
    code_hash: str
    code_salt: str
    attempts: int = 0
    max_attempts: int = PASSWORD_RESET_MAX_ATTEMPTS
    expires_at: datetime = field(
        default_factory=lambda: _now() + timedelta(minutes=PASSWORD_RESET_TTL_MINUTES)
    )
    used_at: datetime | None = None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)

    @classmethod
    def create(cls, *, username: str, code: str) -> PasswordReset:
        salt = secrets.token_bytes(16).hex()
        return cls(
            username=username,
            code_hash=_hash_code(code, salt),
            code_salt=salt,
        )

    @property
    def id(self) -> str:
        return self.id_for(self.username)

    @staticmethod
    def id_for(username: str) -> str:
        return f"PASSWORD_RESET#{username}"

    @property
    def ttl(self) -> int:
        return int(self.expires_at.timestamp())

    def ensure_active(self, now: datetime | None = None) -> None:
        current = now or _now()
        if self.used_at is not None:
            raise InvalidChallengeResponseError(detail="PasswordResetUsed")
        if current >= self.expires_at:
            raise InvalidChallengeResponseError(detail="PasswordResetExpired")
        if self.attempts >= self.max_attempts:
            raise InvalidChallengeResponseError(detail="PasswordResetAttemptsExceeded")

    def verify(self, code: str) -> bool:
        return secrets.compare_digest(_hash_code(code, self.code_salt), self.code_hash)

    def register_failed_attempt(self) -> None:
        self.attempts += 1
        self.updated_at = _now()
        raise InvalidChallengeResponseError(detail="PasswordResetCodeMismatch")

    def mark_used(self) -> None:
        self.used_at = _now()
        self.updated_at = self.used_at
