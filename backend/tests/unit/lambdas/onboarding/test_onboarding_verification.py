from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from lambdas.onboarding.domain.errors import (
    OnboardingOtpAttemptsExceededError,
    OnboardingOtpExpiredError,
    OnboardingOtpInvalidError,
)
from lambdas.onboarding.domain.onboarding_verification import (
    OTP_MAX_ATTEMPTS,
    OTP_TTL_MINUTES,
    OnboardingVerification,
    generate_otp,
)


def _make_verification(**overrides) -> OnboardingVerification:
    otp = overrides.pop("otp", "123456")
    return OnboardingVerification.create(
        ruc="1792146739001",
        email="owner@codelabs.com",
        plan_id="uuid-basic",
        payload_hash="hash",
        self_service=True,
        otp=otp,
        **overrides,
    )


class GenerateOtpTests(unittest.TestCase):
    def test_generates_six_digit_numeric_code(self) -> None:
        otp = generate_otp()

        self.assertEqual(len(otp), 6)
        self.assertTrue(otp.isdigit())


class OnboardingVerificationCreateTests(unittest.TestCase):
    def test_create_hashes_otp_and_sets_defaults(self) -> None:
        verification = _make_verification(otp="123456")

        self.assertNotEqual(verification.otp_hash, "123456")
        self.assertEqual(verification.attempts, 0)
        self.assertEqual(verification.max_attempts, OTP_MAX_ATTEMPTS)
        self.assertIsNone(verification.used_at)

    def test_create_sets_expiry_based_on_otp_ttl(self) -> None:
        before = datetime.now(UTC)
        verification = _make_verification()
        after = datetime.now(UTC)

        expected_min = before + timedelta(minutes=OTP_TTL_MINUTES)
        expected_max = after + timedelta(minutes=OTP_TTL_MINUTES)
        self.assertGreaterEqual(verification.expires_at, expected_min)
        self.assertLessEqual(verification.expires_at, expected_max)

    def test_ttl_matches_expires_at_timestamp(self) -> None:
        verification = _make_verification()

        self.assertEqual(verification.ttl, int(verification.expires_at.timestamp()))


class OnboardingVerificationVerifyTests(unittest.TestCase):
    def test_verify_returns_true_for_correct_otp(self) -> None:
        verification = _make_verification(otp="123456")

        self.assertTrue(verification.verify("123456"))

    def test_verify_returns_false_for_incorrect_otp(self) -> None:
        verification = _make_verification(otp="123456")

        self.assertFalse(verification.verify("000000"))

    def test_ensure_active_raises_when_already_used(self) -> None:
        verification = _make_verification(otp="123456")
        verification.mark_used()

        with self.assertRaises(OnboardingOtpInvalidError):
            verification.ensure_active()

    def test_ensure_active_raises_when_expired(self) -> None:
        verification = _make_verification(otp="123456")
        verification.expires_at = datetime.now(UTC) - timedelta(seconds=1)

        with self.assertRaises(OnboardingOtpExpiredError):
            verification.ensure_active()

    def test_ensure_active_raises_when_attempts_exhausted(self) -> None:
        verification = _make_verification(otp="123456")
        verification.attempts = verification.max_attempts

        with self.assertRaises(OnboardingOtpAttemptsExceededError):
            verification.ensure_active()


class OnboardingVerificationAttemptsTests(unittest.TestCase):
    def test_register_failed_attempt_raises_invalid_below_limit(self) -> None:
        verification = _make_verification(otp="123456")

        with self.assertRaises(OnboardingOtpInvalidError):
            verification.register_failed_attempt()

        self.assertEqual(verification.attempts, 1)

    def test_register_failed_attempt_raises_exceeded_at_limit(self) -> None:
        verification = _make_verification(otp="123456")
        verification.attempts = verification.max_attempts - 1

        with self.assertRaises(OnboardingOtpAttemptsExceededError):
            verification.register_failed_attempt()

        self.assertEqual(verification.attempts, verification.max_attempts)


class OnboardingVerificationMarkUsedTests(unittest.TestCase):
    def test_mark_used_sets_used_at_and_updated_at(self) -> None:
        verification = _make_verification(otp="123456")

        verification.mark_used()

        self.assertIsNotNone(verification.used_at)
        self.assertEqual(verification.updated_at, verification.used_at)


if __name__ == "__main__":
    unittest.main()
