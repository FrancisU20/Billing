from __future__ import annotations

"""
DynamoDB implementation of the Tenant repository.

Does not extend BaseRepository (which is for TenantScopedEntity).
Tenant is a GlobalEntity with its own key logic.

DynamoDB table:
    PK: id (tenant UUID)
    GSI ruc-index: PK=ruc (lookup by RUC)
    RUC uniqueness lock: id="RUC#{ruc}" in the same table

Listing: Scan with FilterExpression (acceptable — few tenants in a B2B SaaS).
"""

from datetime import UTC, datetime

from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

from lambdas._base.idempotency import (
    IdempotencyContext,
    completion_transact_item,
    mark_completed,
)
from lambdas.tenants.domain.dashboard_summary import RecentTenant, TenantAggregateStats
from lambdas.tenants.domain.enums import SriEnvironment, TenantStatus
from lambdas.tenants.domain.errors import TenantNotFoundError, TenantRucAlreadyExistsError
from lambdas.tenants.domain.repositories.i_tenant_repository import ITenantRepository
from lambdas.tenants.domain.tenant import Tenant
from shared.audit.writer import audit_item, audit_put_transact_item
from shared.dates import current_ecuador_month_utc_bounds, current_ecuador_previous_month_utc_bounds
from shared.db.paginator import decode_cursor, encode_cursor
from shared.db.transactions import (
    ExtraTransactionConditionFailedError,
    cancellation_reasons,
    has_conditional_failure_at,
)
from shared.domain.events.domain_event import DomainEvent
from shared.domain.events.outbox import outbox_put_transact_item
from shared.errors import DatabaseError, OptimisticLockError
from shared.logger import get_logger

_log = get_logger(__name__)


def _dt(value: str) -> datetime:
    """Parse an ISO-8601 datetime string, ensuring the result is always timezone-aware."""
    dt = datetime.fromisoformat(value)
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


class DynamoTenantRepository(ITenantRepository):
    def __init__(self, table, audit_table=None, outbox_table=None) -> None:
        self._table = table
        self._audit_table = audit_table
        self._outbox_table = outbox_table

    # ── reads ─────────────────────────────────────────────────────────────────

    def get_by_id(self, tenant_id: str) -> Tenant:
        try:
            resp = self._table.get_item(Key={"id": tenant_id})
        except ClientError as e:
            _log.error("DynamoDB get_item error", error=str(e))
            raise DatabaseError() from e

        item = resp.get("Item")
        if not item or item.get("deleted") or item.get("entity_type", "TENANT") != "TENANT":
            raise TenantNotFoundError()
        return self._from_item(item)

    def get_by_ruc(self, ruc: str) -> Tenant | None:
        try:
            resp = self._table.query(
                IndexName="ruc-index",
                KeyConditionExpression=Key("ruc").eq(ruc),
            )
        except ClientError as e:
            _log.error("DynamoDB ruc-index query error", error=str(e))
            raise DatabaseError() from e

        items = [
            item for item in resp.get("Items", []) if item.get("entity_type", "TENANT") == "TENANT"
        ]
        if not items:
            return None

        active = [item for item in items if not item.get("deleted")]
        return self._from_item((active or items)[0])

    def list(
        self,
        limit: int,
        next_token: str | None,
        status: str | None = None,
        q: str | None = None,
        ruc: str | None = None,
        sri_environment: str | None = None,
        plan_status: str | None = None,
        created_from: str | None = None,
        created_to: str | None = None,
    ) -> tuple[list[Tenant], str | None]:
        filters = _TenantListFilters(
            status=status,
            q=q,
            sri_environment=sri_environment,
            plan_status=plan_status,
            created_from=created_from,
            created_to=created_to,
        )
        now = datetime.now(UTC)

        if ruc:
            tenant = self.get_by_ruc(ruc.strip())
            if not tenant or tenant.deleted:
                return [], None
            if not filters.matches(tenant, now=now):
                return [], None
            return [tenant], None

        kwargs: dict = {"FilterExpression": filters.to_dynamo_filter(), "Limit": limit}
        cursor = decode_cursor(next_token)
        if cursor:
            kwargs["ExclusiveStartKey"] = cursor

        tenants: list[Tenant] = []
        next_cursor = cursor
        while len(tenants) < limit:
            if next_cursor:
                kwargs["ExclusiveStartKey"] = next_cursor
            elif "ExclusiveStartKey" in kwargs:
                del kwargs["ExclusiveStartKey"]
            kwargs["Limit"] = limit - len(tenants)

            try:
                resp = self._table.scan(**kwargs)
            except ClientError as e:
                _log.error("DynamoDB scan error", error=str(e))
                raise DatabaseError() from e

            for item in resp.get("Items", []):
                tenant = self._from_item(item)
                if filters.matches(tenant, now=now):
                    tenants.append(tenant)

            next_cursor = resp.get("LastEvaluatedKey")
            if not next_cursor:
                break

        return tenants, encode_cursor(next_cursor)

    def count(
        self,
        status: str | None = None,
        sri_environment: str | None = None,
        created_from: str | None = None,
        created_to: str | None = None,
    ) -> int:
        """Accurate only when `q`/`plan_status` are not in play — those are
        matched in Python (plan_status is computed at read time, never stored).
        Full-table Scan with Select=COUNT: acceptable for a B2B SaaS tenant
        catalog (same cost class already documented for `list()`)."""
        filters = _TenantListFilters(
            status=status,
            q=None,
            sri_environment=sri_environment,
            plan_status=None,
            created_from=created_from,
            created_to=created_to,
        )
        kwargs: dict = {"FilterExpression": filters.to_dynamo_filter(), "Select": "COUNT"}
        total = 0
        try:
            while True:
                resp = self._table.scan(**kwargs)
                total += resp.get("Count", 0)
                last_key = resp.get("LastEvaluatedKey")
                if not last_key:
                    break
                kwargs["ExclusiveStartKey"] = last_key
        except ClientError as e:
            _log.error("DynamoDB count scan error", error=str(e))
            raise DatabaseError() from e
        return total

    def aggregate_dashboard_stats(self, now: datetime) -> TenantAggregateStats:
        """Single full-table Scan (same cost class as `count()` — small B2B catalog),
        tallied in one Python pass. `active_by_plan_id` only counts
        subscription_status='active' tenants — it is the source for both "top plan"
        and the MRR base in GetSuperadminDashboardUseCase. `recent_tenants` is the
        5 newest tenants — sorted in memory at the end, no extra Scan."""
        month_start, month_end = current_ecuador_month_utc_bounds(now)
        month_start_dt, month_end_dt = _dt(month_start), _dt(month_end)
        prev_month_start, prev_month_end = current_ecuador_previous_month_utc_bounds(now)
        prev_month_start_dt, prev_month_end_dt = _dt(prev_month_start), _dt(prev_month_end)

        total = 0
        new_this_month = 0
        new_previous_month = 0
        by_environment: dict[str, int] = {}
        by_subscription_status: dict[str, int] = {}
        active_by_plan_id: dict[str, int] = {}
        all_tenants: list[Tenant] = []

        kwargs: dict = {
            "FilterExpression": Attr("entity_type").eq("TENANT") & Attr("deleted").eq(False)
        }
        try:
            while True:
                resp = self._table.scan(**kwargs)
                for item in resp.get("Items", []):
                    tenant = self._from_item(item)
                    all_tenants.append(tenant)
                    total += 1
                    if month_start_dt <= tenant.created_at <= month_end_dt:
                        new_this_month += 1
                    elif prev_month_start_dt <= tenant.created_at <= prev_month_end_dt:
                        new_previous_month += 1
                    env = tenant.sri_environment.value
                    by_environment[env] = by_environment.get(env, 0) + 1
                    sub_status = tenant.subscription_status or "none"
                    by_subscription_status[sub_status] = (
                        by_subscription_status.get(sub_status, 0) + 1
                    )
                    if tenant.subscription_status == "active":
                        active_by_plan_id[tenant.plan_id] = (
                            active_by_plan_id.get(tenant.plan_id, 0) + 1
                        )

                last_key = resp.get("LastEvaluatedKey")
                if not last_key:
                    break
                kwargs["ExclusiveStartKey"] = last_key
        except ClientError as e:
            _log.error("DynamoDB aggregate_dashboard_stats scan error", error=str(e))
            raise DatabaseError() from e

        recent_tenants = [
            RecentTenant(id=t.id, trade_name=t.trade_name, created_at=t.created_at.isoformat())
            for t in sorted(all_tenants, key=lambda t: t.created_at, reverse=True)[:5]
        ]

        return TenantAggregateStats(
            total=total,
            new_this_month=new_this_month,
            new_previous_month=new_previous_month,
            by_environment=by_environment,
            by_subscription_status=by_subscription_status,
            active_by_plan_id=active_by_plan_id,
            recent_tenants=recent_tenants,
        )

    def list_with_subscription_expiry_due(self, before: datetime) -> list[Tenant]:
        """Return tenants with a paid plan whose cycle ends before `before`.

        Includes both `active` and `payment_failed` tenants so the renewal worker
        can retry auto-charge during the grace period and force-expire when it ends.
        """
        filter_expr = (
            Attr("entity_type").eq("TENANT")
            & Attr("deleted").eq(False)
            & Attr("status").eq(TenantStatus.ACTIVE.value)
            & (
                Attr("subscription_status").eq("active")
                | Attr("subscription_status").eq("payment_failed")
            )
            & Attr("plan_cycle_ends_at").exists()
            & Attr("plan_cycle_ends_at").lte(before.isoformat())
        )

        tenants: list[Tenant] = []
        scan_kwargs: dict = {"FilterExpression": filter_expr}
        while True:
            try:
                resp = self._table.scan(**scan_kwargs)
            except ClientError as e:
                _log.error("DynamoDB scan error", error=str(e))
                raise DatabaseError() from e

            tenants.extend(self._from_item(item) for item in resp.get("Items", []))

            last_key = resp.get("LastEvaluatedKey")
            if not last_key:
                break
            scan_kwargs["ExclusiveStartKey"] = last_key

        return tenants

    def list_with_certificate_expiry_due(self, before: datetime) -> list[Tenant]:
        filter_expr = (
            Attr("entity_type").eq("TENANT")
            & Attr("deleted").eq(False)
            & Attr("status").ne(TenantStatus.INACTIVE.value)
            & Attr("cert_expires_at").exists()
            & Attr("cert_expires_at").lte(before.isoformat())
        )

        tenants: list[Tenant] = []
        scan_kwargs: dict = {"FilterExpression": filter_expr}
        while True:
            try:
                resp = self._table.scan(**scan_kwargs)
            except ClientError as e:
                _log.error("DynamoDB scan error", error=str(e))
                raise DatabaseError() from e

            tenants.extend(self._from_item(item) for item in resp.get("Items", []))

            last_key = resp.get("LastEvaluatedKey")
            if not last_key:
                break
            scan_kwargs["ExclusiveStartKey"] = last_key

        return tenants

    def list_with_pending_activation(self) -> list[Tenant]:
        """Return pending_payment tenants that have a pending_order_id set (payment confirmed
        but activation transaction never committed)."""
        filter_expr = (
            Attr("entity_type").eq("TENANT")
            & Attr("deleted").eq(False)
            & Attr("subscription_status").eq("pending_payment")
            & Attr("pending_order_id").exists()
        )

        tenants: list[Tenant] = []
        scan_kwargs: dict = {"FilterExpression": filter_expr}
        while True:
            try:
                resp = self._table.scan(**scan_kwargs)
            except ClientError as e:
                _log.error("DynamoDB scan error (list_with_pending_activation)", error=str(e))
                raise DatabaseError() from e

            tenants.extend(self._from_item(item) for item in resp.get("Items", []))

            last_key = resp.get("LastEvaluatedKey")
            if not last_key:
                break
            scan_kwargs["ExclusiveStartKey"] = last_key

        return tenants

    # ── writes ────────────────────────────────────────────────────────────────

    def set_pending_order_id(self, tenant_id: str, order_id: str) -> None:
        """Lightweight pre-activation write. Records the order association before the full
        activation transaction runs so the reconciler can retry if the commit fails."""
        try:
            self._table.update_item(
                Key={"id": tenant_id},
                UpdateExpression="SET pending_order_id = :oid",
                ConditionExpression=("attribute_exists(#id) AND subscription_status = :status"),
                ExpressionAttributeNames={"#id": "id"},
                ExpressionAttributeValues={
                    ":oid": order_id,
                    ":status": "pending_payment",
                },
            )
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            if code == "ConditionalCheckFailedException":
                # Tenant already active or doesn't exist — idempotent no-op.
                return
            _log.error("DynamoDB update_item error (set_pending_order_id)", error=str(exc))
            raise DatabaseError() from exc

    def save(self, tenant: Tenant, user_id: str) -> None:
        self.commit(
            tenant=tenant,
            user_id=user_id,
            action="SAVE",
            events=[],
            idempotency=None,
            response=None,
            extra_transact_items=None,
        )

    def commit(
        self,
        *,
        tenant: Tenant,
        user_id: str,
        action: str,
        events: list[DomainEvent],
        idempotency: IdempotencyContext | None,
        response: dict | None,
        extra_transact_items: list[dict] | None = None,
    ) -> None:
        item = self._to_item(tenant)
        old_raw = self._get_raw(tenant.id)
        is_create = old_raw is None and tenant.version == 1
        transact_items: list[dict] = []

        if is_create:
            transact_items.extend(self._create_items(tenant, item, user_id))
        else:
            transact_items.append(self._update_item(tenant, item))

        if idempotency is not None:
            if response is None:
                raise ValueError("response is required to complete idempotency")
            transact_items.append(completion_transact_item(idempotency, response))

        extra_condition_indexes: set[int] = set()
        if extra_transact_items:
            extra_start = len(transact_items)
            transact_items.extend(extra_transact_items)
            extra_condition_indexes = set(range(extra_start, len(transact_items)))

        if self._outbox_table:
            for event in events:
                transact_items.append(
                    outbox_put_transact_item(
                        self._outbox_table.table_name,
                        event,
                        source="tenants",
                    )
                )

        if self._audit_table:
            transact_items.append(
                audit_put_transact_item(
                    self._audit_table.table_name,
                    audit_item(
                        pk="AUDIT#TENANT",
                        entity_type="TENANT",
                        entity_id=tenant.id,
                        action=action,
                        changed_by=user_id,
                        before=old_raw,
                        after=item,
                    ),
                )
            )

        self._transact_write(
            transact_items,
            idempotency,
            is_create,
            extra_condition_indexes=extra_condition_indexes,
        )

    def commit_admin_events(
        self,
        *,
        tenant: Tenant,
        user_id: str,
        action: str,
        events: list[DomainEvent],
        idempotency: IdempotencyContext | None,
        response: dict | None,
    ) -> None:
        old_raw = self._get_raw(tenant.id)
        if old_raw is None:
            raise TenantNotFoundError()

        transact_items: list[dict] = [self._tenant_unchanged_condition_item(tenant)]

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
                        source="tenants",
                    )
                )

        if self._audit_table:
            transact_items.append(
                audit_put_transact_item(
                    self._audit_table.table_name,
                    audit_item(
                        pk="AUDIT#TENANT",
                        entity_type="TENANT",
                        entity_id=tenant.id,
                        action=action,
                        changed_by=user_id,
                        before=old_raw,
                        after=old_raw,
                    ),
                )
            )

        self._transact_write(
            transact_items,
            idempotency,
            is_create=False,
            extra_condition_indexes=set(),
        )

    # ── internal helpers ──────────────────────────────────────────────────────

    def _get_raw(self, tenant_id: str) -> dict | None:
        try:
            resp = self._table.get_item(Key={"id": tenant_id})
            return resp.get("Item")
        except ClientError as e:
            _log.error("DynamoDB get_item error", error=str(e))
            raise DatabaseError() from e

    def _create_items(self, tenant: Tenant, item: dict, user_id: str) -> list[dict]:
        lock_item = self._ruc_lock_item(tenant, user_id)
        return [
            {
                "Put": {
                    "TableName": self._table.table_name,
                    "Item": lock_item,
                    "ConditionExpression": "attribute_not_exists(#id)",
                    "ExpressionAttributeNames": {"#id": "id"},
                }
            },
            {
                "Put": {
                    "TableName": self._table.table_name,
                    "Item": item,
                    "ConditionExpression": "attribute_not_exists(#id)",
                    "ExpressionAttributeNames": {"#id": "id"},
                }
            },
        ]

    def _update_item(self, tenant: Tenant, item: dict) -> dict:
        return {
            "Put": {
                "TableName": self._table.table_name,
                "Item": item,
                "ConditionExpression": "attribute_exists(#id) AND #version = :prev",
                "ExpressionAttributeNames": {"#id": "id", "#version": "version"},
                "ExpressionAttributeValues": {":prev": tenant.version - 1},
            }
        }

    def _tenant_unchanged_condition_item(self, tenant: Tenant) -> dict:
        return {
            "ConditionCheck": {
                "TableName": self._table.table_name,
                "Key": {"id": tenant.id},
                "ConditionExpression": (
                    "attribute_exists(#id) AND #version = :version AND #deleted = :deleted"
                ),
                "ExpressionAttributeNames": {
                    "#id": "id",
                    "#version": "version",
                    "#deleted": "deleted",
                },
                "ExpressionAttributeValues": {
                    ":version": tenant.version,
                    ":deleted": False,
                },
            }
        }

    def _transact_write(
        self,
        transact_items: list[dict],
        idempotency: IdempotencyContext | None,
        is_create: bool,
        *,
        extra_condition_indexes: set[int],
    ) -> None:
        try:
            self._table.meta.client.transact_write_items(TransactItems=transact_items)
            if idempotency is not None:
                mark_completed()
        except ClientError as e:
            code = e.response["Error"]["Code"]
            if code in ("TransactionCanceledException", "ConditionalCheckFailedException"):
                reasons = cancellation_reasons(e)
                _log.error(
                    "DynamoDB transact_write_items cancelled",
                    is_create=is_create,
                    reasons=reasons,
                    error=str(e),
                )
                if is_create:
                    ruc_lock_failed = reasons and reasons[0].get("code") == "ConditionalCheckFailed"
                    tenant_failed = (
                        len(reasons) > 1 and reasons[1].get("code") == "ConditionalCheckFailed"
                    )
                    if ruc_lock_failed or tenant_failed:
                        raise TenantRucAlreadyExistsError() from e
                    if has_conditional_failure_at(e, extra_condition_indexes):
                        raise ExtraTransactionConditionFailedError() from e
                    raise DatabaseError() from e
                if has_conditional_failure_at(e, extra_condition_indexes):
                    raise ExtraTransactionConditionFailedError() from e
                raise OptimisticLockError() from e
            _log.error("DynamoDB transact_write_items error", error=str(e))
            raise DatabaseError() from e

    def _ruc_lock_item(self, tenant: Tenant, user_id: str) -> dict:
        return {
            "id": f"RUC#{tenant.ruc}",
            "entity_type": "TENANT_RUC_LOCK",
            "tenant_id": tenant.id,
            "locked_ruc": tenant.ruc,
            "created_at": tenant.created_at.isoformat(),
            "created_by": user_id,
        }

    def _to_item(self, tenant: Tenant) -> dict:
        return {
            "entity_type": "TENANT",
            "id": tenant.id,
            "ruc": tenant.ruc,
            "trade_name": tenant.trade_name,
            "legal_name": tenant.legal_name,
            "legal_rep_name": tenant.legal_rep_name,
            "email": tenant.email,
            "phone": tenant.phone,
            "address": tenant.address,
            "accounting_required": tenant.accounting_required,
            "sri_environment": tenant.sri_environment.value,
            "status": tenant.status.value,
            "plan_id": tenant.plan_id,
            "plan_cycle_ends_at": (
                tenant.plan_cycle_ends_at.isoformat() if tenant.plan_cycle_ends_at else None
            ),
            "certificate_secret_arn": tenant.certificate_secret_arn,
            "cert_subject_ruc": tenant.cert_subject_ruc,
            "cert_expires_at": (
                tenant.cert_expires_at.isoformat() if tenant.cert_expires_at else None
            ),
            "cert_issuer": tenant.cert_issuer,
            "cert_uploaded_at": (
                tenant.cert_uploaded_at.isoformat() if tenant.cert_uploaded_at else None
            ),
            "cert_expiry_alert_60_sent_at": (
                tenant.cert_expiry_alert_60_sent_at.isoformat()
                if tenant.cert_expiry_alert_60_sent_at
                else None
            ),
            "cert_expiry_alert_30_sent_at": (
                tenant.cert_expiry_alert_30_sent_at.isoformat()
                if tenant.cert_expiry_alert_30_sent_at
                else None
            ),
            "onboarding_completed_at": (
                tenant.onboarding_completed_at.isoformat()
                if tenant.onboarding_completed_at
                else None
            ),
            "plan_confirmed_at": (
                tenant.plan_confirmed_at.isoformat() if tenant.plan_confirmed_at else None
            ),
            "dlocal_payer_id": tenant.dlocal_payer_id,
            "subscription_status": tenant.subscription_status,
            "subscription_renewal_reminder_sent_at": (
                tenant.subscription_renewal_reminder_sent_at.isoformat()
                if tenant.subscription_renewal_reminder_sent_at
                else None
            ),
            "pending_order_id": tenant.pending_order_id,
            "billing_cycle": tenant.billing_cycle,
            "version": tenant.version,
            "deleted": tenant.deleted,
            "created_at": tenant.created_at.isoformat(),
            "updated_at": tenant.updated_at.isoformat(),
            "created_by": tenant.created_by,
            "updated_by": tenant.updated_by,
            "deleted_at": tenant.deleted_at.isoformat() if tenant.deleted_at else None,
            "deleted_by": tenant.deleted_by,
        }

    def _from_item(self, item: dict) -> Tenant:
        return Tenant(
            id=item["id"],
            ruc=item["ruc"],
            trade_name=item.get("trade_name", ""),
            legal_name=item.get("legal_name", ""),
            legal_rep_name=item.get("legal_rep_name", ""),
            email=item["email"],
            phone=item.get("phone", ""),
            address=item.get("address", ""),
            accounting_required=item.get("accounting_required", False),
            sri_environment=SriEnvironment(item.get("sri_environment", "testing")),
            status=TenantStatus(item.get("status", "active")),
            plan_id=item.get("plan_id", ""),
            plan_cycle_ends_at=_dt(item["plan_cycle_ends_at"])
            if item.get("plan_cycle_ends_at")
            else None,
            certificate_secret_arn=item.get("certificate_secret_arn"),
            cert_subject_ruc=item.get("cert_subject_ruc"),
            cert_expires_at=_dt(item["cert_expires_at"]) if item.get("cert_expires_at") else None,
            cert_issuer=item.get("cert_issuer"),
            cert_uploaded_at=_dt(item["cert_uploaded_at"])
            if item.get("cert_uploaded_at")
            else None,
            cert_expiry_alert_60_sent_at=_dt(item["cert_expiry_alert_60_sent_at"])
            if item.get("cert_expiry_alert_60_sent_at")
            else None,
            cert_expiry_alert_30_sent_at=_dt(item["cert_expiry_alert_30_sent_at"])
            if item.get("cert_expiry_alert_30_sent_at")
            else None,
            onboarding_completed_at=_dt(item["onboarding_completed_at"])
            if item.get("onboarding_completed_at")
            else None,
            plan_confirmed_at=_dt(item["plan_confirmed_at"])
            if item.get("plan_confirmed_at")
            else None,
            dlocal_payer_id=item.get("dlocal_payer_id"),
            subscription_status=item.get("subscription_status"),
            subscription_renewal_reminder_sent_at=_dt(item["subscription_renewal_reminder_sent_at"])
            if item.get("subscription_renewal_reminder_sent_at")
            else None,
            pending_order_id=item.get("pending_order_id"),
            billing_cycle=item.get("billing_cycle", "month"),
            version=item.get("version", 1),
            deleted=item.get("deleted", False),
            created_at=_dt(item["created_at"]),
            updated_at=_dt(item["updated_at"]),
            created_by=item.get("created_by", ""),
            updated_by=item.get("updated_by", ""),
            deleted_at=_dt(item["deleted_at"]) if item.get("deleted_at") else None,
            deleted_by=item.get("deleted_by"),
        )


class _TenantListFilters:
    def __init__(
        self,
        *,
        status: str | None,
        q: str | None,
        sri_environment: str | None,
        plan_status: str | None,
        created_from: str | None,
        created_to: str | None,
    ) -> None:
        self.status = status
        self.needle = q.strip().lower() if q else ""
        self.sri_environment = sri_environment
        self.plan_status = plan_status
        self.created_from = created_from
        self.created_to = created_to

    def to_dynamo_filter(self):
        # plan_status is computed at read time (Tenant.effective_plan_status) —
        # it is never stored, so it cannot appear in a DynamoDB FilterExpression.
        # It is matched in-memory below, alongside the free-text search.
        filter_expr = Attr("entity_type").eq("TENANT") & Attr("deleted").eq(False)
        if self.status:
            filter_expr = filter_expr & Attr("status").eq(self.status)
        if self.sri_environment:
            filter_expr = filter_expr & Attr("sri_environment").eq(self.sri_environment)
        if self.created_from:
            filter_expr = filter_expr & Attr("created_at").gte(self.created_from)
        if self.created_to:
            filter_expr = filter_expr & Attr("created_at").lte(self.created_to)
        return filter_expr

    def matches(self, tenant: Tenant, *, now: datetime) -> bool:
        if self.status and tenant.status.value != self.status:
            return False
        if self.sri_environment and tenant.sri_environment.value != self.sri_environment:
            return False
        if self.plan_status and tenant.effective_plan_status(now).value != self.plan_status:
            return False
        created_at = tenant.created_at.isoformat()
        if self.created_from and created_at < self.created_from:
            return False
        if self.created_to and created_at > self.created_to:
            return False
        if not self.needle:
            return True
        return (
            self.needle in tenant.trade_name.lower()
            or self.needle in tenant.legal_rep_name.lower()
            or self.needle in tenant.email.lower()
            or self.needle in tenant.ruc.lower()
        )
