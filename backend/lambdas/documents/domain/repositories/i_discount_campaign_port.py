from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class DiscountCampaignSnapshot:
    active: bool
    percentage: Decimal


class IDiscountCampaignPort(ABC):
    @abstractmethod
    def get_active_campaign(self) -> DiscountCampaignSnapshot:
        """Return the tenant's discount campaign (inactive/0% if never configured)."""
