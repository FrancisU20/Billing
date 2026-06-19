from __future__ import annotations

from decimal import Decimal

from lambdas.products.domain.discount_campaign import DiscountCampaign
from lambdas.products.domain.repositories.i_discount_campaign_repository import (
    IDiscountCampaignRepository,
)


class UpdateDiscountCampaignUseCase:
    def __init__(self, repo: IDiscountCampaignRepository) -> None:
        self._repo = repo

    def execute(self, *, active: bool, percentage: Decimal, updated_by: str) -> DiscountCampaign:
        campaign = self._repo.get()
        campaign.update(active=active, percentage=percentage, updated_by=updated_by)
        return campaign
