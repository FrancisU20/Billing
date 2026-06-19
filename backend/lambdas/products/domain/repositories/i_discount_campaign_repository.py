from __future__ import annotations

from abc import ABC, abstractmethod

from lambdas.products.domain.discount_campaign import DiscountCampaign


class IDiscountCampaignRepository(ABC):
    @abstractmethod
    def get(self) -> DiscountCampaign:
        """Return the tenant's discount campaign, or a default (inactive) one."""

    @abstractmethod
    def save(
        self,
        *,
        campaign: DiscountCampaign,
        user_id: str,
        action: str,
        idempotency,
        response: dict | None,
    ) -> None:
        """Persist campaign plus audit/idempotency state."""
