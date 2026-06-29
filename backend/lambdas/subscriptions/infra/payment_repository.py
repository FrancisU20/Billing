from __future__ import annotations

from datetime import UTC, datetime

from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

from lambdas.subscriptions.domain.entities.payment import Payment, PaymentStatus
from lambdas.subscriptions.domain.errors import PaymentNotFoundError
from lambdas.subscriptions.domain.repositories.i_payment_repository import IPaymentRepository
from shared.errors import DatabaseError
from shared.logger import get_logger

_log = get_logger(__name__)

_AUTO_RENEWAL_RECONCILIATION_PREFIX = "AUTO_RENEWAL_RECONCILIATION"


class DynamoPaymentRepository(IPaymentRepository):
    def __init__(self, table) -> None:
        self._table = table

    def save(self, payment: Payment) -> None:
        try:
            self._table.put_item(Item=self._to_item(payment))
        except ClientError as exc:
            _log.error("DynamoDB put_item error", error=str(exc))
            raise DatabaseError() from exc

    def save_transact_item(self, payment: Payment) -> dict:
        return {
            "Put": {
                "TableName": self._table.table_name,
                "Item": self._to_item(payment),
                "ConditionExpression": "attribute_not_exists(id)",
            }
        }

    def link_tenant(self, order_id: str, tenant_id: str) -> None:
        try:
            self._table.update_item(
                Key={"id": f"PAYMENT#{order_id}"},
                UpdateExpression="SET tenant_id = :tid",
                ExpressionAttributeValues={":tid": tenant_id},
            )
        except ClientError as exc:
            _log.error("DynamoDB update_item error (link_tenant)", error=str(exc))
            raise DatabaseError() from exc

    def apply_webhook_status(
        self, order_id: str, new_status: PaymentStatus
    ) -> tuple[PaymentStatus, bool]:
        condition, values = _webhook_transition_condition(new_status)
        now = datetime.now(UTC).isoformat()
        update_expression = "SET #status = :new_status"
        if new_status == "PAID":
            update_expression += ", confirmed_at = if_not_exists(confirmed_at, :now)"
            values[":now"] = now

        try:
            resp = self._table.update_item(
                Key={"id": f"PAYMENT#{order_id}"},
                UpdateExpression=update_expression,
                ConditionExpression=f"attribute_exists(id) AND {condition}",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues=values,
                ReturnValues="ALL_NEW",
            )
            updated = resp.get("Attributes", {})
            return updated.get("status", new_status), True
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") != "ConditionalCheckFailedException":
                _log.error("DynamoDB update_item error (apply_webhook_status)", error=str(exc))
                raise DatabaseError() from exc
            current = self.get_by_order_id(order_id)
            return current.status, False

    def list_stale_open_payments(self, *, cutoff: datetime) -> list[Payment]:
        cutoff_iso = cutoff.isoformat()
        payments: list[Payment] = []
        scan_kwargs: dict = {
            "FilterExpression": (
                Attr("status").is_in(["CREATED", "PENDING"]) & Attr("created_at").lte(cutoff_iso)
            )
        }
        try:
            while True:
                resp = self._table.scan(**scan_kwargs)
                for item in resp.get("Items", []):
                    payments.append(self._from_item(item))
                last_key = resp.get("LastEvaluatedKey")
                if not last_key:
                    break
                scan_kwargs["ExclusiveStartKey"] = last_key
        except ClientError as exc:
            _log.error("DynamoDB scan error (stale open payments)", error=str(exc))
            raise DatabaseError() from exc
        return payments

    def cancel_stale_open_payment(self, *, order_id: str, cutoff: datetime) -> bool:
        try:
            self._table.update_item(
                Key={"id": f"PAYMENT#{order_id}"},
                UpdateExpression="SET #status = :cancelled, error_detail = :detail",
                ConditionExpression=(
                    "attribute_exists(id) AND #status IN (:created, :pending) "
                    "AND created_at <= :cutoff"
                ),
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":cancelled": "CANCELLED",
                    ":detail": "Expired by stale payment cleaner",
                    ":created": "CREATED",
                    ":pending": "PENDING",
                    ":cutoff": cutoff.isoformat(),
                },
            )
            return True
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                return False
            _log.error("DynamoDB update_item error (cancel stale payment)", error=str(exc))
            raise DatabaseError() from exc

    def create_auto_renewal_reconciliation_marker(
        self,
        *,
        tenant_id: str,
        cycle_ends_at: datetime,
        plan_id: str,
        amount: str,
        currency: str,
        reason: str,
    ) -> bool:
        item = {
            "id": _auto_renewal_reconciliation_id(tenant_id, cycle_ends_at),
            "record_type": _AUTO_RENEWAL_RECONCILIATION_PREFIX,
            "tenant_id": tenant_id,
            "tenant_cycle_ends_at": cycle_ends_at.isoformat(),
            "plan_id": plan_id,
            "amount": amount,
            "currency": currency,
            "status": "STARTED",
            "reconciliation_reason": reason,
            "created_at": datetime.now(UTC).isoformat(),
        }
        try:
            self._table.put_item(
                Item=item,
                ConditionExpression="attribute_not_exists(id)",
            )
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                return False
            _log.error(
                "DynamoDB put_item error (auto renewal reconciliation start)",
                tenant_id=tenant_id,
                error=str(exc),
            )
            raise DatabaseError() from exc
        return True

    def save_auto_renewal_reconciliation_marker(
        self,
        payment: Payment,
        *,
        tenant_id: str,
        cycle_ends_at: datetime,
        reason: str,
    ) -> None:
        item = self._to_item(payment)
        item["id"] = _auto_renewal_reconciliation_id(tenant_id, cycle_ends_at)
        item["record_type"] = _AUTO_RENEWAL_RECONCILIATION_PREFIX
        item["external_order_id"] = payment.order_id
        item["tenant_cycle_ends_at"] = cycle_ends_at.isoformat()
        item["reconciliation_reason"] = reason
        try:
            self._table.put_item(Item=item)
        except ClientError as exc:
            _log.error(
                "DynamoDB put_item error (auto renewal reconciliation)",
                tenant_id=tenant_id,
                order_id=payment.order_id,
                error=str(exc),
            )
            raise DatabaseError() from exc

    def delete_auto_renewal_reconciliation_marker(
        self, *, tenant_id: str, cycle_ends_at: datetime
    ) -> None:
        try:
            self._table.delete_item(
                Key={"id": _auto_renewal_reconciliation_id(tenant_id, cycle_ends_at)}
            )
        except ClientError as exc:
            _log.error(
                "DynamoDB delete_item error (auto renewal reconciliation)",
                tenant_id=tenant_id,
                error=str(exc),
            )
            raise DatabaseError() from exc

    def link_tenant_transact_item(self, order_id: str, tenant_id: str) -> dict:
        return {
            "Update": {
                "TableName": self._table.table_name,
                "Key": {"id": f"PAYMENT#{order_id}"},
                "UpdateExpression": "SET tenant_id = :tid",
                "ExpressionAttributeValues": {":tid": tenant_id},
            }
        }

    def get_by_order_id(self, order_id: str) -> Payment:
        try:
            resp = self._table.get_item(Key={"id": f"PAYMENT#{order_id}"})
        except ClientError as exc:
            _log.error("DynamoDB get_item error", error=str(exc))
            raise DatabaseError() from exc

        item = resp.get("Item")
        if not item:
            raise PaymentNotFoundError()
        return self._from_item(item)

    def _to_item(self, payment: Payment) -> dict:
        item: dict = {
            "id": f"PAYMENT#{payment.order_id}",
            "order_id": payment.order_id,
            "plan_id": payment.plan_id,
            "amount": payment.amount,
            "currency": payment.currency,
            "status": payment.status,
            "plan_cycle": payment.plan_cycle,
            "created_at": payment.created_at.isoformat(),
        }
        if payment.checkout_token:
            item["checkout_token"] = payment.checkout_token
        if payment.confirmed_at:
            item["confirmed_at"] = payment.confirmed_at.isoformat()
        if payment.payer_id:
            item["payer_id"] = payment.payer_id
        if payment.payer_email:
            item["payer_email"] = payment.payer_email
        if payment.tenant_id:
            item["tenant_id"] = payment.tenant_id
        if payment.error_detail:
            item["error_detail"] = payment.error_detail
        return item

    def _from_item(self, item: dict) -> Payment:
        return Payment(
            order_id=item.get("order_id", ""),
            tenant_id=item.get("tenant_id"),
            plan_id=item.get("plan_id", ""),
            amount=item.get("amount", "0.00"),
            currency=item.get("currency", "USD"),
            status=item.get("status", "CREATED"),
            plan_cycle=item.get("plan_cycle", "month"),
            checkout_token=item.get("checkout_token"),
            created_at=datetime.fromisoformat(item["created_at"]),
            confirmed_at=datetime.fromisoformat(item["confirmed_at"])
            if item.get("confirmed_at")
            else None,
            payer_id=item.get("payer_id"),
            payer_email=item.get("payer_email"),
            error_detail=item.get("error_detail"),
        )


def _auto_renewal_reconciliation_id(tenant_id: str, cycle_ends_at: datetime) -> str:
    return f"{_AUTO_RENEWAL_RECONCILIATION_PREFIX}#{tenant_id}#{cycle_ends_at.isoformat()}"


def _webhook_transition_condition(new_status: PaymentStatus) -> tuple[str, dict]:
    if new_status == "PAID":
        return (
            "#status <> :paid AND #status <> :refunded",
            {
                ":new_status": new_status,
                ":paid": "PAID",
                ":refunded": "REFUNDED",
            },
        )
    return (
        "#status IN (:created, :pending)",
        {
            ":new_status": new_status,
            ":created": "CREATED",
            ":pending": "PENDING",
        },
    )
