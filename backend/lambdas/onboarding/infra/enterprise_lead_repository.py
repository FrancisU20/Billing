from __future__ import annotations

"""
DynamoDB implementation of the EnterpriseLead repository.

Leads are stored in the `tenants` table (entity_type=ENTERPRISE_LEAD), keyed
by their own UUID — they do not share the RUC lock or any key space with
Tenant records.
"""

from botocore.exceptions import ClientError

from lambdas._base.idempotency import (
    IdempotencyContext,
    completion_transact_item,
    mark_completed,
)
from lambdas.onboarding.domain.enterprise_lead import EnterpriseLead
from lambdas.onboarding.domain.repositories.i_enterprise_lead_repository import (
    IEnterpriseLeadRepository,
)
from shared.domain.events.domain_event import DomainEvent
from shared.domain.events.outbox import outbox_put_transact_item
from shared.errors import DatabaseError
from shared.logger import get_logger

_log = get_logger(__name__)


class DynamoEnterpriseLeadRepository(IEnterpriseLeadRepository):
    def __init__(self, table, outbox_table=None) -> None:
        self._table = table
        self._outbox_table = outbox_table

    def commit(
        self,
        *,
        lead: EnterpriseLead,
        events: list[DomainEvent],
        idempotency: IdempotencyContext | None,
        response: dict | None,
    ) -> None:
        transact_items: list[dict] = [
            {
                "Put": {
                    "TableName": self._table.table_name,
                    "Item": self._to_item(lead),
                    "ConditionExpression": "attribute_not_exists(#id)",
                    "ExpressionAttributeNames": {"#id": "id"},
                }
            }
        ]

        if idempotency is not None:
            if response is None:
                raise ValueError("response is required to complete idempotency")
            transact_items.append(completion_transact_item(idempotency, response))

        if self._outbox_table:
            for event in events:
                transact_items.append(
                    outbox_put_transact_item(
                        self._outbox_table.table_name,
                        event,
                        source="onboarding",
                    )
                )

        try:
            self._table.meta.client.transact_write_items(TransactItems=transact_items)
            if idempotency is not None:
                mark_completed()
        except ClientError as exc:
            _log.error("DynamoDB transact_write_items error", error=str(exc))
            raise DatabaseError()

    def _to_item(self, lead: EnterpriseLead) -> dict:
        return {
            "id": lead.id,
            "entity_type": "ENTERPRISE_LEAD",
            "ruc": lead.ruc,
            "trade_name": lead.trade_name,
            "legal_name": lead.legal_name,
            "legal_rep_name": lead.legal_rep_name,
            "email": lead.email,
            "phone": lead.phone,
            "address": lead.address,
            "accounting_required": lead.accounting_required,
            "plan_id": lead.plan_id,
            "version": lead.version,
            "created_at": lead.created_at.isoformat(),
            "updated_at": lead.updated_at.isoformat(),
            "created_by": lead.created_by,
            "updated_by": lead.updated_by,
        }
