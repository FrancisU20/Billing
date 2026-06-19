from __future__ import annotations

from lambdas.products.domain.discount_campaign import DiscountCampaign
from lambdas.products.domain.repositories.i_discount_campaign_repository import (
    IDiscountCampaignRepository,
)


class GetDiscountCampaignUseCase:
    def __init__(self, repo: IDiscountCampaignRepository) -> None:
        self._repo = repo

    def execute(self) -> DiscountCampaign:
        return self._repo.get()
