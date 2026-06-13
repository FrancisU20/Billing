from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class PlanSummary:
    id: str
    self_service: bool
    limit_cycle: str


class IPlanCatalog(ABC):
    @abstractmethod
    def get(self, plan_id: str) -> PlanSummary:
        """Look up a plan for onboarding.

        Raises PlanNotFoundError if the plan does not exist or is deleted,
        PlanNotActiveError if it exists but is not active.
        """
