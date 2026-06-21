from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal

from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

from lambdas.tenants.domain.dashboard_summary import DailyRevenuePoint, PaymentRevenueStats
from lambdas.tenants.domain.errors import SubscriptionRenewalPaymentNotFoundError
from lambdas.tenants.domain.repositories.i_payment_reader import IPaymentReader, PaymentRecord
from shared.dates import (
    current_ecuador_month_utc_bounds,
    current_ecuador_previous_month_utc_bounds,
    current_ecuador_previous_year_utc_bounds,
    current_ecuador_year_utc_bounds,
    to_ecuador,
)
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
                # attribute_not_exists covers payments where tenant_id was never written
                # (omitted when None — payment_repository._to_item skips falsy tenant_id).
                "ConditionExpression": ("attribute_not_exists(tenant_id) OR tenant_id = :tid"),
                "ExpressionAttributeValues": {
                    ":tid": tenant_id,
                },
            }
        }

    def aggregate_revenue(self, now: datetime) -> PaymentRevenueStats:
        """Single Scan of `status=PAID` payments. Buckets gross `amount` into the
        current/previous calendar month and year, AND into a daily series for the
        last 30 Ecuador-civil days — one pass over the table covers every revenue
        stat the dashboard needs (no separate Scan per metric)."""
        month_start, month_end = current_ecuador_month_utc_bounds(now)
        prev_month_start, prev_month_end = current_ecuador_previous_month_utc_bounds(now)
        year_start, year_end = current_ecuador_year_utc_bounds(now)
        prev_year_start, prev_year_end = current_ecuador_previous_year_utc_bounds(now)

        today = to_ecuador(now).date()
        daily_buckets: dict[str, Decimal] = {
            (today - timedelta(days=offset)).isoformat(): Decimal("0.00")
            for offset in range(29, -1, -1)
        }

        gross_this_month = Decimal("0.00")
        gross_previous_month = Decimal("0.00")
        gross_this_year = Decimal("0.00")
        gross_previous_year = Decimal("0.00")

        kwargs: dict = {"FilterExpression": Attr("status").eq("PAID")}
        try:
            while True:
                resp = self._table.scan(**kwargs)
                for item in resp.get("Items", []):
                    confirmed_at = item.get("confirmed_at")
                    if not confirmed_at:
                        continue
                    amount = Decimal(str(item.get("amount", "0.00")))

                    if year_start <= confirmed_at <= year_end:
                        gross_this_year += amount
                    elif prev_year_start <= confirmed_at <= prev_year_end:
                        gross_previous_year += amount

                    if month_start <= confirmed_at <= month_end:
                        gross_this_month += amount
                    elif prev_month_start <= confirmed_at <= prev_month_end:
                        gross_previous_month += amount

                    civil_date = to_ecuador(datetime.fromisoformat(confirmed_at)).date().isoformat()
                    if civil_date in daily_buckets:
                        daily_buckets[civil_date] += amount

                last_key = resp.get("LastEvaluatedKey")
                if not last_key:
                    break
                kwargs["ExclusiveStartKey"] = last_key
        except ClientError as exc:
            _log.error("DynamoDB aggregate_revenue scan error", error=str(exc))
            raise DatabaseError() from exc

        daily_last_30_days = [
            DailyRevenuePoint(date=date, amount=amount) for date, amount in daily_buckets.items()
        ]

        return PaymentRevenueStats(
            gross_this_month=gross_this_month,
            gross_previous_month=gross_previous_month,
            gross_this_year=gross_this_year,
            gross_previous_year=gross_previous_year,
            daily_last_30_days=daily_last_30_days,
        )
