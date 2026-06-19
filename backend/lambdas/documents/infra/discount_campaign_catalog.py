from __future__ import annotations

"""Local adapter from documents lambda to the products lambda's discount campaign table."""

from lambdas.documents.domain.repositories.i_discount_campaign_port import (
    DiscountCampaignSnapshot,
    IDiscountCampaignPort,
)
from lambdas.products.infra.discount_campaign_repository import DynamoDiscountCampaignRepository


class DynamoDiscountCampaignCatalog(IDiscountCampaignPort):
    def __init__(self, tenant_id: str, table) -> None:
        self._repo = DynamoDiscountCampaignRepository(tenant_id, table)

    def get_active_campaign(self) -> DiscountCampaignSnapshot:
        campaign = self._repo.get()
        return DiscountCampaignSnapshot(active=campaign.active, percentage=campaign.percentage)
