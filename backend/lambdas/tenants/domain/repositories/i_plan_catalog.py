from __future__ import annotations

from abc import ABC, abstractmethod


class IPlanCatalog(ABC):
    @abstractmethod
    def ensure_active(self, plan_id: str) -> None:
        """Validate that the plan exists and can be assigned to a tenant."""
