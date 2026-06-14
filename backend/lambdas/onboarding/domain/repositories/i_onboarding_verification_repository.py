from __future__ import annotations

from abc import ABC, abstractmethod

from lambdas._base.idempotency import IdempotencyContext
from lambdas.onboarding.domain.onboarding_verification import OnboardingVerification
from shared.domain.events.domain_event import DomainEvent


class IOnboardingVerificationRepository(ABC):
    @abstractmethod
    def get_by_id(self, verification_id: str) -> OnboardingVerification:
        """Raises OnboardingVerificationNotFoundError when missing."""

    @abstractmethod
    def commit_request(
        self,
        *,
        verification: OnboardingVerification,
        events: list[DomainEvent],
        idempotency: IdempotencyContext | None,
        response: dict | None,
    ) -> None:
        """Persist verification + outbox + idempotency in one transaction."""

    @abstractmethod
    def save_attempts(self, verification: OnboardingVerification) -> None:
        """Persist failed OTP attempts."""

    @abstractmethod
    def mark_used(self, verification: OnboardingVerification) -> None:
        """Mark a verification as consumed."""

    @abstractmethod
    def mark_used_transact_item(self, verification: OnboardingVerification) -> dict:
        """Build a TransactWriteItems entry that marks the verification as consumed."""
