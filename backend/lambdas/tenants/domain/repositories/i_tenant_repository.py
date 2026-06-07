from __future__ import annotations

from abc import ABC, abstractmethod

from lambdas._base.idempotency import IdempotencyContext
from lambdas.tenants.domain.tenant import Tenant
from shared.domain.events.domain_event import DomainEvent


class ITenantRepository(ABC):

    @abstractmethod
    def get_by_id(self, tenant_id: str) -> Tenant:
        """Raises TenantNotFoundError if not found or soft-deleted."""

    @abstractmethod
    def get_by_ruc(self, ruc: str) -> Tenant | None:
        """Returns None if not found. Includes soft-deleted: RUC is never recycled."""

    @abstractmethod
    def save(self, tenant: Tenant, user_id: str) -> None:
        """Create or update. Raises OptimisticLockError on concurrent modification."""

    @abstractmethod
    def list(
        self,
        limit:      int,
        next_token: str | None,
        status:     str | None = None,
    ) -> tuple[list[Tenant], str | None]:
        """Returns (items, next_token). next_token=None if no more pages."""

    @abstractmethod
    def commit(
        self,
        *,
        tenant:      Tenant,
        user_id:     str,
        action:      str,
        events:      list[DomainEvent],
        idempotency: IdempotencyContext | None,
        response:    dict | None,
    ) -> None:
        """Atomic commit: entity + audit + outbox + idempotency in one transaction."""
