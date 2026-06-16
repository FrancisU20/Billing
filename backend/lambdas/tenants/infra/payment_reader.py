from __future__ import annotations

from botocore.exceptions import ClientError

from lambdas.tenants.domain.errors import SubscriptionRenewalPaymentNotFoundError
from lambdas.tenants.domain.repositories.i_payment_reader import IPaymentReader, PaymentRecord
from shared.errors import DatabaseError
from shared.logger import get_logger

_log = get_logger(__name__)


class DynamoPaymentReader(IPaymentReader):
    def __init__(self, payments_table) -> None:
        self._table = payments_table

    def get_by_order_id(self, order_id: str) -> PaymentRecord:
        try:
            resp = self._table.get_item(Key={"id": f"PAYMENT#{order_id}"})
        except ClientError as exc:
            _log.error("DynamoDB get_item error (payment reader)", error=str(exc))
            raise DatabaseError() from exc

        item = resp.get("Item")
        if not item:
            raise SubscriptionRenewalPaymentNotFoundError()

        return PaymentRecord(
            order_id=item.get("order_id", ""),
            tenant_id=item.get("tenant_id", ""),
            plan_id=item.get("plan_id", ""),
            amount=item.get("amount", "0.00"),
            status=item.get("status", "CREATED"),
            plan_cycle=item.get("plan_cycle", "month"),
            payer_id=item.get("payer_id", ""),
        )

    def mark_applied_to_tenant(self, order_id: str, tenant_id: str) -> dict:
        return {
            "Update": {
                "TableName": self._table.table_name,
                "Key": {"id": f"PAYMENT#{order_id}"},
                "UpdateExpression": "SET tenant_id = :tid",
                # Guard: only if not yet applied to a different tenant.
                "ConditionExpression": "tenant_id = :empty OR tenant_id = :tid",
                "ExpressionAttributeValues": {
                    ":tid": tenant_id,
                    ":empty": "",
                },
            }
        }
