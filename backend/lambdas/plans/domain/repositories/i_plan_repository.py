from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from lambdas.plans.domain.plan import Plan


class IPlanRepository(ABC):
    @abstractmethod
    def get_by_id(self, plan_id: str) -> Plan:
        """Look up by UUID — used internally (update, toggle)."""

    @abstractmethod
    def get_by_slug(self, slug: str) -> Plan:
        """Look up by slug via GSI — used on public routes."""

    @abstractmethod
    def save(self, plan: Plan) -> None: ...

    @abstractmethod
    def commit(
        self,
        *,
        plan: Plan,
        user_id: str,
        action: str,
        idempotency: Any | None,
        response: dict | None,
    ) -> None: ...

    @abstractmethod
    def list(
        self,
        *,
        status: str | None = None,
        slug: str | None = None,
        q: str | None = None,
        limit_cycle: str | None = None,
        created_from: str | None = None,
        created_to: str | None = None,
    ) -> list[Plan]: ...
