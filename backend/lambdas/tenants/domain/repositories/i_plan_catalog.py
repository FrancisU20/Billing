from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from lambdas.tenants.domain.dashboard_summary import PlanPricing


@dataclass(frozen=True)
class SelfServicePlanInfo:
    limit_cycle: str
    is_free: bool


class IPlanCatalog(ABC):
    @abstractmethod
    def ensure_active(self, plan_id: str) -> str:
        """Validate that the plan exists and can be assigned to a tenant.

        Returns the plan's `limit_cycle` ("month" | "year") so the tenant can
        compute its plan-cycle expiration date at creation time.
        """

    @abstractmethod
    def ensure_self_service_active(self, plan_id: str) -> SelfServicePlanInfo:
        """Validate the plan exists, is active, and is self-service.

        Raises TenantPlanNotSelfServiceError for Enterprise plans (assisted sales).
        """

    @abstractmethod
    def get_pricing(self, plan_ids: set[str]) -> dict[str, PlanPricing]:
        """Pricing for a handful of plan_ids (small catalog, one get_item per id —
        same cost class as `ensure_active()`). Missing/deleted plan_ids are omitted
        from the result, not raised as an error (a dashboard stat outliving a
        deleted plan should degrade gracefully, not break the whole summary)."""
