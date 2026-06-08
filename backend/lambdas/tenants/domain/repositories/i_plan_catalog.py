from __future__ import annotations

from abc import ABC, abstractmethod


class IPlanCatalog(ABC):
    @abstractmethod
    def ensure_active(self, plan_id: str) -> str:
        """Validate that the plan exists and can be assigned to a tenant.

        Returns the plan's `limit_cycle` ("month" | "year") so the tenant can
        compute its plan-cycle expiration date at creation time.
        """
