from __future__ import annotations

"""DynamoDB repository for the tenant's discount campaign — a singleton item per tenant."""

from datetime import datetime
from decimal import Decimal

from botocore.exceptions import ClientError

from lambdas._base.idempotency import (
    IdempotencyContext,
    completion_transact_item,
    mark_completed,
)
from lambdas.products.domain.discount_campaign import DiscountCampaign
from lambdas.products.domain.repositories.i_discount_campaign_repository import (
    IDiscountCampaignRepository,
)
from shared.audit.writer import audit_item, audit_put_transact_item
from shared.db.base_repository import BaseRepository
from shared.errors import DatabaseError, OptimisticLockError
from shared.logger import get_logger

_log = get_logger(__name__)
_SINGLETON_ID = "default"


class DynamoDiscountCampaignRepository(BaseRepository, IDiscountCampaignRepository):
    _prefix = "DISCOUNT_CAMPAIGN"

    def get(self) -> DiscountCampaign:
        item = self._get_raw(_SINGLETON_ID)
        if not item:
            return DiscountCampaign.default(self._tenant_id)
        return self._from_item(item)

    def save(
        self,
        *,
        campaign: DiscountCampaign,
        user_id: str,
        action: str,
        idempotency: IdempotencyContext | None,
        response: dict | None,
    ) -> None:
        old_raw = self._raw_by_key()
        item = self._to_item(campaign)
        prev_version = campaign.version - 1

        transact_items: list[dict] = [
            {
                "Put": {
                    "TableName": self._table.table_name,
                    "Item": item,
                    "ConditionExpression": ("attribute_not_exists(#pk) OR #version = :prev"),
                    "ExpressionAttributeNames": {"#pk": "pk", "#version": "version"},
                    "ExpressionAttributeValues": {":prev": prev_version},
                }
            }
        ]

        if idempotency is not None:
            if response is None:
                raise ValueError("response is required to complete idempotency")
            transact_items.append(completion_transact_item(idempotency, response))

        if self._audit_table:
            transact_items.append(
                audit_put_transact_item(
                    self._audit_table.table_name,
                    audit_item(
                        pk=f"AUDIT#{self._tenant_id}",
                        entity_type="DISCOUNT_CAMPAIGN",
                        entity_id=_SINGLETON_ID,
                        action=action,
                        changed_by=user_id,
                        before=old_raw,
                        after=item,
                    ),
                )
            )

        try:
            self._table.meta.client.transact_write_items(TransactItems=transact_items)
            if idempotency is not None:
                mark_completed()
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            if code in ("TransactionCanceledException", "ConditionalCheckFailedException"):
                _log.error("DynamoDB transact_write_items cancelled", error=str(exc))
                raise OptimisticLockError() from exc
            _log.error("DynamoDB transact_write_items error", error=str(exc))
            raise DatabaseError() from exc

    def _raw_by_key(self) -> dict | None:
        try:
            response = self._table.get_item(Key={"pk": self._pk(), "sk": self._sk(_SINGLETON_ID)})
            return response.get("Item")
        except ClientError as exc:
            _log.error("DynamoDB get_item error", error=str(exc))
            raise DatabaseError() from exc

    def _to_item(self, campaign: DiscountCampaign) -> dict:
        return {
            "entity_type": "DISCOUNT_CAMPAIGN",
            "pk": self._pk(),
            "sk": self._sk(_SINGLETON_ID),
            "id": _SINGLETON_ID,
            "tenant_id": campaign.tenant_id,
            "active": campaign.active,
            "percentage": str(campaign.percentage),
            "version": campaign.version,
            "created_at": campaign.created_at.isoformat(),
            "updated_at": campaign.updated_at.isoformat(),
            "created_by": campaign.created_by,
            "updated_by": campaign.updated_by,
        }

    def _from_item(self, item: dict) -> DiscountCampaign:
        return DiscountCampaign(
            id=_SINGLETON_ID,
            tenant_id=item["tenant_id"],
            active=bool(item.get("active", False)),
            percentage=Decimal(str(item.get("percentage", "0.00"))),
            version=item.get("version", 1),
            created_at=datetime.fromisoformat(item["created_at"]),
            updated_at=datetime.fromisoformat(item["updated_at"]),
            created_by=item.get("created_by", ""),
            updated_by=item.get("updated_by", ""),
        )
