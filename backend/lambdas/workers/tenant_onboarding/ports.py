from __future__ import annotations

"""Application ports for tenant onboarding."""

from abc import ABC, abstractmethod

from shared.domain.events.domain_event import DomainEvent


class IdentityProvider(ABC):
    @abstractmethod
    def create_owner(self, *, tenant_id: str, email: str, temporary_password: str) -> bool:
        """Create the tenant owner user.
        Returns True if created, False if it already existed.
        """

    @abstractmethod
    def reset_temporary_password(self, *, email: str, temporary_password: str) -> bool:
        """Set a new temporary password for users still in onboarding.
        Returns True if the password was reset and should be emailed.
        """


class EventPublisherPort(ABC):
    @abstractmethod
    def publish(self, event: DomainEvent) -> None:
        """Publish a domain event to the corresponding queue."""
