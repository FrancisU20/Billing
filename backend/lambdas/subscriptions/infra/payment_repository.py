from __future__ import annotations

from datetime import datetime

from botocore.exceptions import ClientError

from lambdas.subscriptions.domain.entities.payment import Payment
from lambdas.subscriptions.domain.errors import PaymentNotFoundError
from lambdas.subscriptions.domain.repositories.i_payment_repository import IPaymentRepository
from shared.errors import DatabaseError
from shared.logger import get_logger

_log = get_logger(__name__)


class DynamoPaymentRepository(IPaymentRepository):
    def __init__(self, table) -> None:
        self._table = table

    def save(self, payment: Payment) -> None:
        try:
            self._table.put_item(Item=self._to_item(payment))
        except ClientError as exc:
            _log.error("DynamoDB put_item error", error=str(exc))
            raise DatabaseError() from exc

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
        if payment.captured_at:
            item["captured_at"] = payment.captured_at.isoformat()
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
            created_at=datetime.fromisoformat(item["created_at"]),
            captured_at=datetime.fromisoformat(item["captured_at"])
            if item.get("captured_at")
            else None,
            payer_id=item.get("payer_id"),
            payer_email=item.get("payer_email"),
            error_detail=item.get("error_detail"),
        )
