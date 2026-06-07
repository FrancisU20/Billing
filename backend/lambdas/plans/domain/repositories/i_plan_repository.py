from abc import ABC, abstractmethod

from lambdas.plans.domain.plan import Plan


class IPlanRepository(ABC):
    @abstractmethod
    def get_by_id(self, plan_id: str) -> Plan:
        """Busca por UUID — usado internamente (update, toggle)."""

    @abstractmethod
    def get_by_slug(self, slug: str) -> Plan:
        """Busca por slug via GSI — usado en rutas públicas."""

    @abstractmethod
    def save(self, plan: Plan) -> None: ...

    @abstractmethod
    def list(self, active_only: bool = False) -> list[Plan]: ...
