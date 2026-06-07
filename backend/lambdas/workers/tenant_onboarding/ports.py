"""Application ports for tenant onboarding."""
from __future__ import annotations

from abc import ABC, abstractmethod

from shared.domain.events.domain_event import DomainEvent


class IdentityProvider(ABC):
    @abstractmethod
    def create_owner(
        self, *, tenant_id: str, email: str, temporary_password: str
    ) -> bool:
        """Create the tenant owner user.
        Returns True if created, False if it already existed.
        """


class EventPublisherPort(ABC):
    @abstractmethod
    def publish(self, event: DomainEvent) -> None:
        """Publish a domain event to the corresponding queue."""
