from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class PlanSummary:
    id: str
    monthly_price: Decimal
    annual_price: Decimal
    limit_cycle: str
    is_free: bool


class IPlanCatalog(ABC):
    @abstractmethod
    def get(self, plan_id: str) -> PlanSummary: ...
