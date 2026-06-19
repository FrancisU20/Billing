from __future__ import annotations

import unittest
from decimal import Decimal

from lambdas.products.domain.discount_campaign import DiscountCampaign
from lambdas.products.use_cases.get_discount_campaign import GetDiscountCampaignUseCase
from lambdas.products.use_cases.update_discount_campaign import UpdateDiscountCampaignUseCase
from shared.errors import ValidationError


class FakeDiscountCampaignRepository:
    def __init__(self) -> None:
        self.campaign: DiscountCampaign | None = None
        self.save_calls: list[dict] = []

    def get(self) -> DiscountCampaign:
        if self.campaign is None:
            return DiscountCampaign.default("tenant-1")
        return self.campaign

    def save(self, **kwargs) -> None:
        self.save_calls.append(kwargs)


class DiscountCampaignTests(unittest.TestCase):
    def test_default_campaign_is_inactive(self) -> None:
        campaign = DiscountCampaign.default("tenant-1")

        self.assertFalse(campaign.active)
        self.assertEqual(campaign.percentage, Decimal("0.00"))

    def test_get_use_case_returns_default_when_never_configured(self) -> None:
        campaign = GetDiscountCampaignUseCase(FakeDiscountCampaignRepository()).execute()

        self.assertFalse(campaign.active)

    def test_update_use_case_activates_campaign(self) -> None:
        repo = FakeDiscountCampaignRepository()

        campaign = UpdateDiscountCampaignUseCase(repo).execute(
            active=True, percentage=Decimal("50"), updated_by="user-1"
        )

        self.assertTrue(campaign.active)
        self.assertEqual(campaign.percentage, Decimal("50.00"))
        self.assertEqual(campaign.updated_by, "user-1")

    def test_update_use_case_reuses_existing_version_for_optimistic_lock(self) -> None:
        repo = FakeDiscountCampaignRepository()
        repo.campaign = DiscountCampaign(id="default", tenant_id="tenant-1", version=3)

        campaign = UpdateDiscountCampaignUseCase(repo).execute(
            active=False, percentage=Decimal("0"), updated_by="user-2"
        )

        self.assertEqual(campaign.version, 4)

    def test_rejects_percentage_above_100(self) -> None:
        with self.assertRaises(ValidationError):
            UpdateDiscountCampaignUseCase(FakeDiscountCampaignRepository()).execute(
                active=True, percentage=Decimal("100.01"), updated_by="user-1"
            )

    def test_rejects_negative_percentage(self) -> None:
        with self.assertRaises(ValidationError):
            UpdateDiscountCampaignUseCase(FakeDiscountCampaignRepository()).execute(
                active=True, percentage=Decimal("-1"), updated_by="user-1"
            )


if __name__ == "__main__":
    unittest.main()
