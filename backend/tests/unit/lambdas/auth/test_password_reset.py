from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from lambdas.auth.domain.errors import InvalidChallengeResponseError
from lambdas.auth.domain.password_reset import (
    PASSWORD_RESET_MAX_ATTEMPTS,
    PASSWORD_RESET_TTL_MINUTES,
    PasswordReset,
    generate_reset_code,
)


class PasswordResetTests(unittest.TestCase):
    def test_generate_reset_code_returns_six_digits(self) -> None:
        code = generate_reset_code()

        self.assertEqual(len(code), 6)
        self.assertTrue(code.isdigit())

    def test_create_hashes_code_and_sets_ttl(self) -> None:
        before = datetime.now(UTC)
        reset = PasswordReset.create(username="owner@example.com", code="123456")
        after = datetime.now(UTC)

        self.assertEqual(reset.username, "owner@example.com")
        self.assertNotEqual(reset.code_hash, "123456")
        self.assertEqual(reset.attempts, 0)
        self.assertEqual(reset.max_attempts, PASSWORD_RESET_MAX_ATTEMPTS)
        self.assertGreaterEqual(
            reset.expires_at,
            before + timedelta(minutes=PASSWORD_RESET_TTL_MINUTES),
        )
        self.assertLessEqual(
            reset.expires_at,
            after + timedelta(minutes=PASSWORD_RESET_TTL_MINUTES),
        )
        self.assertEqual(reset.ttl, int(reset.expires_at.timestamp()))

    def test_verify_matches_only_original_code(self) -> None:
        reset = PasswordReset.create(username="owner@example.com", code="123456")

        self.assertTrue(reset.verify("123456"))
        self.assertFalse(reset.verify("000000"))

    def test_ensure_active_rejects_expired_used_or_attempts_exceeded(self) -> None:
        expired = PasswordReset.create(username="owner@example.com", code="123456")
        expired.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        with self.assertRaises(InvalidChallengeResponseError):
            expired.ensure_active()

        used = PasswordReset.create(username="owner@example.com", code="123456")
        used.mark_used()
        with self.assertRaises(InvalidChallengeResponseError):
            used.ensure_active()

        blocked = PasswordReset.create(username="owner@example.com", code="123456")
        blocked.attempts = blocked.max_attempts
        with self.assertRaises(InvalidChallengeResponseError):
            blocked.ensure_active()

    def test_register_failed_attempt_increments_and_rejects(self) -> None:
        reset = PasswordReset.create(username="owner@example.com", code="123456")

        with self.assertRaises(InvalidChallengeResponseError):
            reset.register_failed_attempt()

        self.assertEqual(reset.attempts, 1)


if __name__ == "__main__":
    unittest.main()
