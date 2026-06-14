from __future__ import annotations

from abc import ABC, abstractmethod

from lambdas._base.idempotency import IdempotencyContext
from lambdas.onboarding.domain.enterprise_lead import EnterpriseLead
from shared.domain.events.domain_event import DomainEvent


class IEnterpriseLeadRepository(ABC):
    @abstractmethod
    def commit(
        self,
        *,
        lead: EnterpriseLead,
        events: list[DomainEvent],
        idempotency: IdempotencyContext | None,
        response: dict | None,
        extra_transact_items: list[dict] | None = None,
    ) -> None:
        """Atomic commit: lead + outbox + idempotency in one transaction."""
