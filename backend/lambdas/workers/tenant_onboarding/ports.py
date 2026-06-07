"""Puertos de aplicación para tenant onboarding."""
from __future__ import annotations

from abc import ABC, abstractmethod

from shared.domain.events.domain_event import DomainEvent


class IdentityProvider(ABC):
    @abstractmethod
    def create_owner(
        self, *, tenant_id: str, email: str, temporary_password: str
    ) -> bool:
        """Crea el usuario owner del tenant.
        Retorna True si fue creado, False si ya existía.
        """


class EventPublisherPort(ABC):
    @abstractmethod
    def publish(self, event: DomainEvent) -> None:
        """Publica un evento de dominio a la cola correspondiente."""
