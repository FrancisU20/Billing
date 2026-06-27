from __future__ import annotations

"""
DynamoDB implementation of IDocumentsRepository.

Table `documents`:
  PK = "TENANT#{tenant_id}"
  SK = "DOC#{document_id}"
  tenant_id  = tenant_id           (denormalized — GSI partition key)
  created_at = ISO-8601 datetime   (GSI sort key)

GSI `tenant-docs-index`:
  PK = tenant_id
  SK = created_at
  projection = ALL
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

from lambdas._base.idempotency import IdempotencyContext, completion_transact_item, mark_completed
from lambdas.documents.domain.entities import (
    BuyerNotificationStatus,
    DailyIssuedCount,
    Document,
    DocumentStatus,
    DocumentSummary,
    InvoiceLine,
    TopClientTotal,
)
from lambdas.documents.domain.errors import (
    DocumentNotAuthorizedError,
    DocumentNotFoundError,
    DocumentRetryNotEligibleError,
)
from lambdas.documents.domain.repositories.i_documents_repository import IDocumentsRepository
from shared.audit.writer import audit_item, audit_put_transact_item
from shared.dates import current_ecuador_month_utc_bounds, now_ecuador, now_utc, to_ecuador
from shared.db.paginator import decode_cursor, encode_cursor
from shared.errors import DatabaseError
from shared.logger import get_logger

_log = get_logger(__name__)

_GSI = "tenant-docs-index"


def _dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _date_range(start: date, end: date) -> list[date]:
    days = (end - start).days
    return [start + timedelta(days=offset) for offset in range(days + 1)]


def _digits_only(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


class DynamoDocumentsRepository(IDocumentsRepository):
    def __init__(self, table, audit_table=None) -> None:
        self._table = table
        self._audit_table = audit_table

    # ── keys ──────────────────────────────────────────────────────────────────

    def _pk(self, tenant_id: str) -> str:
        return f"TENANT#{tenant_id}"

    def _sk(self, document_id: str) -> str:
        return f"DOC#{document_id}"

    # ── reads ─────────────────────────────────────────────────────────────────

    def get(self, tenant_id: str, document_id: str) -> Document:
        try:
            resp = self._table.get_item(
                Key={"pk": self._pk(tenant_id), "sk": self._sk(document_id)}
            )
        except ClientError as exc:
            _log.error("DynamoDB get_item error (documents)", error=str(exc))
            raise DatabaseError() from exc

        item = resp.get("Item")
        if not item or item.get("deleted"):
            raise DocumentNotFoundError()
        return self._from_item(item)

    def get_many(self, tenant_id: str, document_ids: list[str]) -> dict[str, Document]:
        result: dict[str, Document] = {}
        for document_id in dict.fromkeys(document_ids):
            try:
                resp = self._table.get_item(
                    Key={"pk": self._pk(tenant_id), "sk": self._sk(document_id)}
                )
            except ClientError as exc:
                _log.warning("DynamoDB get_item error (get_many)", error=str(exc))
                continue
            item = resp.get("Item")
            if not item or item.get("deleted"):
                continue
            result[document_id] = self._from_item(item)
        return result

    def _list_filter_expr(
        self,
        status: str | None,
        serie: str | None,
        date_from: str | None,
        date_to: str | None,
        doc_type: str | None = None,
    ):
        filters = [Attr("deleted").ne(True)]
        if status:
            filters.append(Attr("status").eq(status))
        if doc_type:
            filters.append(Attr("doc_type").eq(doc_type))
        if serie:
            filters.append(Attr("serie").eq(serie))
        if date_from:
            filters.append(Attr("issued_at").gte(date_from))
        if date_to:
            filters.append(Attr("issued_at").lte(date_to))

        filter_expr = filters[0]
        for f in filters[1:]:
            filter_expr = filter_expr & f
        return filter_expr

    def _matches_search(self, item: dict, q: str | None) -> bool:
        query = (q or "").strip()
        if not query:
            return True

        query_text = query.casefold()
        query_digits = _digits_only(query)
        serie = str(item.get("serie") or "")
        try:
            sequential = int(item.get("sequential") or 0)
        except (TypeError, ValueError):
            sequential = 0
        sequential_padded = str(sequential).zfill(9)
        sequential_display = (
            f"{serie[:3]}-{serie[3:]}-{sequential_padded}"
            if len(serie) == 6
            else f"{serie}-{sequential_padded}"
        )
        buyer_id = str(item.get("buyer_id") or "")
        buyer_name = str(item.get("buyer_name") or "")
        access_key = str(item.get("access_key") or "")

        text_candidates = [serie, sequential_display, buyer_id, buyer_name, access_key]
        if any(query_text in candidate.casefold() for candidate in text_candidates):
            return True

        if not query_digits:
            return False

        digit_candidates = [
            _digits_only(serie),
            sequential_padded,
            f"{_digits_only(serie)}{sequential_padded}",
            _digits_only(buyer_id),
            _digits_only(access_key),
        ]
        return any(query_digits in candidate for candidate in digit_candidates)

    def list(
        self,
        tenant_id: str,
        *,
        status: str | None = None,
        doc_type: str | None = None,
        serie: str | None = None,
        q: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 20,
        cursor: str | None = None,
    ) -> tuple[list[Document], str | None]:
        has_search = bool((q or "").strip())
        kwargs: dict = {
            "IndexName": _GSI,
            "KeyConditionExpression": Key("tenant_id").eq(tenant_id),
            "FilterExpression": self._list_filter_expr(status, serie, date_from, date_to, doc_type),
            "ScanIndexForward": False,
        }
        if not has_search:
            kwargs["Limit"] = limit
        start_key = decode_cursor(cursor)
        if start_key:
            kwargs["ExclusiveStartKey"] = start_key

        documents: list[Document] = []
        next_cursor = None
        try:
            if not has_search:
                resp = self._table.query(**kwargs)
                items = resp.get("Items", [])
                next_cursor = encode_cursor(resp.get("LastEvaluatedKey"))
                return [self._from_item(item) for item in items], next_cursor

            while len(documents) < limit:
                kwargs["Limit"] = limit - len(documents)
                resp = self._table.query(**kwargs)
                documents.extend(
                    self._from_item(item)
                    for item in resp.get("Items", [])
                    if self._matches_search(item, q)
                )
                last_key = resp.get("LastEvaluatedKey")
                next_cursor = encode_cursor(last_key)
                if len(documents) >= limit or not last_key:
                    break
                kwargs["ExclusiveStartKey"] = last_key
        except ClientError as exc:
            _log.error("DynamoDB query error (documents list)", error=str(exc))
            raise DatabaseError() from exc

        return documents[:limit], next_cursor

    def count(
        self,
        tenant_id: str,
        *,
        status: str | None = None,
        doc_type: str | None = None,
        serie: str | None = None,
        q: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> int:
        kwargs: dict = {
            "IndexName": _GSI,
            "KeyConditionExpression": Key("tenant_id").eq(tenant_id),
            "FilterExpression": self._list_filter_expr(status, serie, date_from, date_to, doc_type),
        }
        if not (q or "").strip():
            kwargs["Select"] = "COUNT"
        total = 0
        try:
            while True:
                resp = self._table.query(**kwargs)
                if (q or "").strip():
                    total += sum(
                        1 for item in resp.get("Items", []) if self._matches_search(item, q)
                    )
                else:
                    total += resp.get("Count", 0)
                last_key = resp.get("LastEvaluatedKey")
                if not last_key:
                    break
                kwargs["ExclusiveStartKey"] = last_key
        except ClientError as exc:
            _log.error("DynamoDB count error (documents)", error=str(exc))
            raise DatabaseError() from exc
        return total

    def count_this_month(self, tenant_id: str, sri_environment: str) -> int:
        start_utc, end_utc = current_ecuador_month_utc_bounds()
        total = 0
        last_key = None
        try:
            while True:
                kwargs: dict = {
                    "IndexName": _GSI,
                    "KeyConditionExpression": (
                        Key("tenant_id").eq(tenant_id)
                        & Key("created_at").between(start_utc, end_utc)
                    ),
                    "FilterExpression": (
                        Attr("sri_environment").eq(sri_environment) & Attr("deleted").ne(True)
                    ),
                    "Select": "COUNT",
                }
                if last_key:
                    kwargs["ExclusiveStartKey"] = last_key
                resp = self._table.query(**kwargs)
                total += resp.get("Count", 0)
                last_key = resp.get("LastEvaluatedKey")
                if not last_key:
                    break
        except ClientError as exc:
            _log.error("DynamoDB count_this_month error", error=str(exc))
            raise DatabaseError() from exc
        return total

    def summary_this_month(self, tenant_id: str) -> DocumentSummary:
        start_utc, end_utc = current_ecuador_month_utc_bounds()
        local_now = now_ecuador()
        period_start = local_now.replace(day=1).date().isoformat()
        period_end = local_now.date().isoformat()
        status_counts = {status.value: 0 for status in DocumentStatus}
        authorized_total = Decimal("0.00")
        credit_notes_count = 0
        credit_notes_total = Decimal("0.00")
        daily_counts: dict[str, int] = {}
        client_totals: dict[str, dict] = {}
        last_key = None

        try:
            while True:
                kwargs: dict = {
                    "IndexName": _GSI,
                    "KeyConditionExpression": (
                        Key("tenant_id").eq(tenant_id)
                        & Key("created_at").between(start_utc, end_utc)
                    ),
                    "FilterExpression": Attr("deleted").ne(True),
                }
                if last_key:
                    kwargs["ExclusiveStartKey"] = last_key

                resp = self._table.query(**kwargs)
                for item in resp.get("Items", []):
                    status = str(item.get("status") or "")
                    if status not in status_counts:
                        continue
                    status_counts[status] += 1

                    issued_day = to_ecuador(_dt(str(item.get("created_at")))).date().isoformat()
                    daily_counts[issued_day] = daily_counts.get(issued_day, 0) + 1

                    if status == DocumentStatus.AUTHORIZED.value:
                        total = Decimal(str(item.get("total", "0.00")))
                        doc_type = str(item.get("doc_type") or "01")
                        if doc_type == "04":
                            # Nota de credito: resta del ingreso neto en vez de sumarse
                            # como si fuera una factura adicional. No afecta top_clients
                            # en v1 (decision documentada — invoice-only, evita rankings
                            # negativos).
                            authorized_total -= total
                            credit_notes_count += 1
                            credit_notes_total += total
                            continue
                        authorized_total += total
                        client_id = item.get("client_id")
                        if client_id:
                            entry = client_totals.setdefault(
                                client_id,
                                {
                                    "name": str(item.get("buyer_name") or ""),
                                    "total": Decimal("0.00"),
                                },
                            )
                            entry["total"] += total

                last_key = resp.get("LastEvaluatedKey")
                if not last_key:
                    break
        except ClientError as exc:
            _log.error("DynamoDB summary_this_month error", error=str(exc))
            raise DatabaseError() from exc

        failed_count = (
            status_counts[DocumentStatus.FAILED.value]
            + status_counts[DocumentStatus.FAILED_PERMANENT.value]
        )
        daily_issued = [
            DailyIssuedCount(date=day.isoformat(), count=daily_counts.get(day.isoformat(), 0))
            for day in _date_range(date.fromisoformat(period_start), date.fromisoformat(period_end))
        ]
        top_clients = [
            TopClientTotal(client_id=client_id, name=entry["name"], total=entry["total"])
            for client_id, entry in sorted(
                client_totals.items(), key=lambda pair: pair[1]["total"], reverse=True
            )[:5]
        ]
        return DocumentSummary(
            period_start=period_start,
            period_end=period_end,
            issued_count=sum(status_counts.values()),
            authorized_count=status_counts[DocumentStatus.AUTHORIZED.value],
            rejected_count=status_counts[DocumentStatus.REJECTED.value],
            failed_count=failed_count,
            pending_count=status_counts[DocumentStatus.PENDING.value],
            processing_count=status_counts[DocumentStatus.PROCESSING.value],
            authorized_total=authorized_total.quantize(Decimal("0.01")),
            credit_notes_count=credit_notes_count,
            credit_notes_total=credit_notes_total.quantize(Decimal("0.01")),
            daily_issued=daily_issued,
            top_clients=top_clients,
        )

    # ── write ─────────────────────────────────────────────────────────────────

    def save(
        self,
        document: Document,
        *,
        idempotency: IdempotencyContext | None = None,
        response: dict | None = None,
        override_reason: str | None = None,
        user_id: str | None = None,
    ) -> None:
        item = self._to_item(document)
        transact_items: list[dict] = [
            {
                "Put": {
                    "TableName": self._table.table_name,
                    "Item": item,
                    "ConditionExpression": "attribute_not_exists(#pk)",
                    "ExpressionAttributeNames": {"#pk": "pk"},
                }
            }
        ]
        if idempotency is not None:
            if response is None:
                raise ValueError("response is required when idempotency context is provided")
            transact_items.append(completion_transact_item(idempotency, response))

        if override_reason and self._audit_table:
            transact_items.append(
                audit_put_transact_item(
                    self._audit_table.table_name,
                    audit_item(
                        pk=f"AUDIT#{document.tenant_id}",
                        entity_type="DOCUMENT",
                        entity_id=document.document_id,
                        action="DISCOUNT_CEILING_OVERRIDE",
                        changed_by=user_id or "",
                        before=None,
                        after={"reason": override_reason, "access_key": document.access_key},
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
                reasons = [
                    {"code": r.get("Code", "None"), "msg": r.get("Message", "")}
                    for r in exc.response.get("CancellationReasons", [])
                ]
                _log.error(
                    "DynamoDB save document transaction cancelled",
                    reasons=reasons,
                )
            _log.error("DynamoDB save document error", error=str(exc))
            raise DatabaseError() from exc

    def annul(
        self,
        tenant_id: str,
        document_id: str,
        *,
        reason: str,
        user_id: str,
        access_key: str,
        idempotency: IdempotencyContext | None = None,
        response: dict | None = None,
    ) -> None:
        now = now_utc().isoformat()

        transact_items: list[dict] = [
            {
                "Update": {
                    "TableName": self._table.table_name,
                    "Key": {"pk": self._pk(tenant_id), "sk": self._sk(document_id)},
                    "UpdateExpression": (
                        "SET #status = :new_status, #updated_at = :updated_at, "
                        "#annulled_at = :annulled_at, #annulled_by = :annulled_by, "
                        "#annulment_reason = :annulment_reason"
                    ),
                    "ConditionExpression": "#status = :expected_status",
                    "ExpressionAttributeNames": {
                        "#status": "status",
                        "#updated_at": "updated_at",
                        "#annulled_at": "annulled_at",
                        "#annulled_by": "annulled_by",
                        "#annulment_reason": "annulment_reason",
                    },
                    "ExpressionAttributeValues": {
                        ":new_status": DocumentStatus.ANNULLED.value,
                        ":expected_status": DocumentStatus.AUTHORIZED.value,
                        ":updated_at": now,
                        ":annulled_at": now,
                        ":annulled_by": user_id,
                        ":annulment_reason": reason,
                    },
                }
            }
        ]
        if self._audit_table:
            transact_items.append(
                audit_put_transact_item(
                    self._audit_table.table_name,
                    audit_item(
                        pk=f"AUDIT#{tenant_id}",
                        entity_type="DOCUMENT",
                        entity_id=document_id,
                        action="DOCUMENT_ANNULLED",
                        changed_by=user_id,
                        before={"status": DocumentStatus.AUTHORIZED.value},
                        after={
                            "status": DocumentStatus.ANNULLED.value,
                            "reason": reason,
                            "access_key": access_key,
                        },
                    ),
                )
            )
        if idempotency is not None:
            if response is None:
                raise ValueError("response is required when idempotency context is provided")
            transact_items.append(completion_transact_item(idempotency, response))

        try:
            self._table.meta.client.transact_write_items(TransactItems=transact_items)
            if idempotency is not None:
                mark_completed()
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            if code in ("TransactionCanceledException", "ConditionalCheckFailedException"):
                _log.warning(
                    "annul no-op: document status already changed",
                    document_id=document_id,
                )
                raise DocumentNotAuthorizedError() from exc
            _log.error("DynamoDB annul document error", error=str(exc))
            raise DatabaseError() from exc

    def retry(
        self,
        tenant_id: str,
        document_id: str,
        *,
        user_id: str,
        access_key: str,
        idempotency: IdempotencyContext | None = None,
        response: dict | None = None,
    ) -> None:
        now = now_utc().isoformat()

        transact_items: list[dict] = [
            {
                "Update": {
                    "TableName": self._table.table_name,
                    "Key": {"pk": self._pk(tenant_id), "sk": self._sk(document_id)},
                    "UpdateExpression": (
                        "SET #status = :new_status, #updated_at = :updated_at, "
                        "#retried_at = :retried_at "
                        "ADD #manual_retry_count :one"
                    ),
                    "ConditionExpression": "#status = :expected_status",
                    "ExpressionAttributeNames": {
                        "#status": "status",
                        "#updated_at": "updated_at",
                        "#retried_at": "retried_at",
                        "#manual_retry_count": "manual_retry_count",
                    },
                    "ExpressionAttributeValues": {
                        ":new_status": DocumentStatus.PENDING.value,
                        ":expected_status": DocumentStatus.REJECTED.value,
                        ":updated_at": now,
                        ":retried_at": now,
                        ":one": 1,
                    },
                }
            }
        ]
        if self._audit_table:
            transact_items.append(
                audit_put_transact_item(
                    self._audit_table.table_name,
                    audit_item(
                        pk=f"AUDIT#{tenant_id}",
                        entity_type="DOCUMENT",
                        entity_id=document_id,
                        action="DOCUMENT_RETRIED",
                        changed_by=user_id,
                        before={"status": DocumentStatus.REJECTED.value},
                        after={"status": DocumentStatus.PENDING.value, "access_key": access_key},
                    ),
                )
            )
        if idempotency is not None:
            if response is None:
                raise ValueError("response is required when idempotency context is provided")
            transact_items.append(completion_transact_item(idempotency, response))

        try:
            self._table.meta.client.transact_write_items(TransactItems=transact_items)
            if idempotency is not None:
                mark_completed()
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            if code in ("TransactionCanceledException", "ConditionalCheckFailedException"):
                _log.warning(
                    "retry no-op: document status already changed",
                    document_id=document_id,
                )
                raise DocumentRetryNotEligibleError() from exc
            _log.error("DynamoDB retry document error", error=str(exc))
            raise DatabaseError() from exc

    def update_status(
        self,
        tenant_id: str,
        document_id: str,
        *,
        expected_status: DocumentStatus,
        new_status: DocumentStatus,
        increment_retry: bool = False,
        authorization_number: str | None = None,
        authorized_at: datetime | None = None,
        rejected_at: datetime | None = None,
        xml_s3_key: str | None = None,
        ride_s3_key: str | None = None,
        sri_errors: list[dict] | None = None,
    ) -> bool:
        now = now_utc().isoformat()
        names = {"#status": "status", "#updated_at": "updated_at"}
        values: dict = {
            ":new_status": new_status.value,
            ":expected_status": expected_status.value,
            ":updated_at": now,
        }
        set_clauses = ["#status = :new_status", "#updated_at = :updated_at"]

        optional_fields = {
            "authorization_number": authorization_number,
            "authorized_at": authorized_at.isoformat() if authorized_at else None,
            "rejected_at": rejected_at.isoformat() if rejected_at else None,
            "xml_s3_key": xml_s3_key,
            "ride_s3_key": ride_s3_key,
            "sri_errors": sri_errors,
        }
        for field_name, field_value in optional_fields.items():
            if field_value is None:
                continue
            placeholder = f":{field_name}"
            names[f"#{field_name}"] = field_name
            values[placeholder] = field_value
            set_clauses.append(f"#{field_name} = {placeholder}")

        update_expression = "SET " + ", ".join(set_clauses)
        if increment_retry:
            update_expression += " ADD retry_count :one"
            values[":one"] = 1

        try:
            self._table.update_item(
                Key={"pk": self._pk(tenant_id), "sk": self._sk(document_id)},
                UpdateExpression=update_expression,
                ConditionExpression="#status = :expected_status",
                ExpressionAttributeNames=names,
                ExpressionAttributeValues=values,
            )
            return True
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                _log.warning(
                    "update_status no-op: document status already changed",
                    document_id=document_id,
                    expected_status=expected_status.value,
                )
                return False
            _log.error("DynamoDB update_status error", error=str(exc))
            raise DatabaseError() from exc

    def mark_buyer_notification_status(
        self,
        tenant_id: str,
        document_id: str,
        *,
        status: BuyerNotificationStatus,
        notified_at: datetime | None = None,
        error: str | None = None,
    ) -> bool:
        now = now_utc().isoformat()
        names = {
            "#status": "buyer_notification_status",
            "#updated_at": "updated_at",
        }
        values: dict = {
            ":status": status.value,
            ":updated_at": now,
            ":sent": BuyerNotificationStatus.SENT.value,
            ":skipped": BuyerNotificationStatus.SKIPPED_NO_EMAIL.value,
            ":null_type": "NULL",
        }
        set_clauses = ["#status = :status", "#updated_at = :updated_at"]

        if notified_at is not None:
            names["#notified_at"] = "buyer_notified_at"
            values[":notified_at"] = notified_at.isoformat()
            set_clauses.append("#notified_at = :notified_at")
        if error is not None:
            names["#error"] = "buyer_notification_error"
            values[":error"] = error[:500]
            set_clauses.append("#error = :error")

        try:
            self._table.update_item(
                Key={"pk": self._pk(tenant_id), "sk": self._sk(document_id)},
                UpdateExpression="SET " + ", ".join(set_clauses),
                ConditionExpression=(
                    "attribute_not_exists(#status) OR attribute_type(#status, :null_type) "
                    "OR (#status <> :sent AND #status <> :skipped)"
                ),
                ExpressionAttributeNames=names,
                ExpressionAttributeValues=values,
            )
            return True
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                _log.info(
                    "buyer notification status already terminal; no-op",
                    document_id=document_id,
                    status=status.value,
                )
                return False
            _log.error("DynamoDB mark_buyer_notification_status error", error=str(exc))
            raise DatabaseError() from exc

    def mark_annulled_by_credit_note(
        self,
        tenant_id: str,
        document_id: str,
        *,
        credit_note_id: str,
    ) -> None:
        # Sin ConditionExpression: EmitCreditNoteUseCase ya bloquea crear una segunda NC
        # de anulacion (parent.annulled_by_credit_note_id is not None), asi que sobreescribir
        # aqui siempre es seguro — nunca hay dos llamadas validas en paralelo para la
        # misma factura.
        try:
            self._table.update_item(
                Key={"pk": self._pk(tenant_id), "sk": self._sk(document_id)},
                UpdateExpression="SET #annulled_by_cn = :credit_note_id, #updated_at = :updated_at",
                ExpressionAttributeNames={
                    "#annulled_by_cn": "annulled_by_credit_note_id",
                    "#updated_at": "updated_at",
                },
                ExpressionAttributeValues={
                    ":credit_note_id": credit_note_id,
                    ":updated_at": now_utc().isoformat(),
                },
            )
        except ClientError as exc:
            _log.error("DynamoDB mark_annulled_by_credit_note error", error=str(exc))
            raise DatabaseError() from exc

    def begin_buyer_notification(self, tenant_id: str, document_id: str) -> bool:
        now = now_utc().isoformat()
        names = {
            "#status": "buyer_notification_status",
            "#updated_at": "updated_at",
        }
        values = {
            ":sending": BuyerNotificationStatus.SENDING.value,
            ":updated_at": now,
            ":pending": BuyerNotificationStatus.PENDING.value,
            ":failed": BuyerNotificationStatus.FAILED.value,
            ":null_type": "NULL",
        }
        try:
            self._table.update_item(
                Key={"pk": self._pk(tenant_id), "sk": self._sk(document_id)},
                UpdateExpression="SET #status = :sending, #updated_at = :updated_at",
                ConditionExpression=(
                    "attribute_not_exists(#status) OR attribute_type(#status, :null_type) "
                    "OR #status = :pending OR #status = :failed"
                ),
                ExpressionAttributeNames=names,
                ExpressionAttributeValues=values,
            )
            return True
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                _log.info(
                    "buyer notification already claimed or terminal; no-op",
                    document_id=document_id,
                )
                return False
            _log.error("DynamoDB begin_buyer_notification error", error=str(exc))
            raise DatabaseError() from exc

    # ── serialization ─────────────────────────────────────────────────────────

    def _to_item(self, doc: Document) -> dict:
        return {
            "pk": self._pk(doc.tenant_id),
            "sk": self._sk(doc.document_id),
            "entity_type": "INVOICE",
            "tenant_id": doc.tenant_id,
            "document_id": doc.document_id,
            "doc_type": doc.doc_type,
            "status": doc.status.value,
            "serie": doc.serie,
            "sequential": doc.sequential,
            "access_key": doc.access_key,
            "client_id": doc.client_id,
            "buyer_id_type": doc.buyer_id_type,
            "buyer_id": doc.buyer_id,
            "buyer_name": doc.buyer_name,
            "buyer_email": doc.buyer_email,
            "issued_at": doc.issued_at.isoformat(),
            "sri_environment": doc.sri_environment,
            "subtotal": str(doc.subtotal),
            "total_discount": str(doc.total_discount),
            "iva_15": str(doc.iva_15),
            "iva_5": str(doc.iva_5),
            "iva_0": str(doc.iva_0),
            "total": str(doc.total),
            "payment_method": doc.payment_method,
            "lines": [ln.to_dict() for ln in doc.lines],
            "retry_count": doc.retry_count,
            "deleted": doc.deleted,
            "created_at": doc.created_at.isoformat(),
            "updated_at": doc.updated_at.isoformat(),
            "created_by": doc.created_by,
            "authorization_number": doc.authorization_number,
            "authorized_at": doc.authorized_at.isoformat() if doc.authorized_at else None,
            "rejected_at": doc.rejected_at.isoformat() if doc.rejected_at else None,
            "xml_s3_key": doc.xml_s3_key,
            "ride_s3_key": doc.ride_s3_key,
            "sri_errors": doc.sri_errors,
            "buyer_notification_status": (
                doc.buyer_notification_status.value if doc.buyer_notification_status else None
            ),
            "buyer_notified_at": doc.buyer_notified_at.isoformat()
            if doc.buyer_notified_at
            else None,
            "buyer_notification_error": doc.buyer_notification_error,
            "annulled_at": doc.annulled_at.isoformat() if doc.annulled_at else None,
            "annulled_by": doc.annulled_by,
            "annulment_reason": doc.annulment_reason,
            "related_document_id": doc.related_document_id,
            "credit_note_reason": doc.credit_note_reason,
            "manual_retry_count": doc.manual_retry_count,
            "retried_at": doc.retried_at.isoformat() if doc.retried_at else None,
            "annulled_by_credit_note_id": doc.annulled_by_credit_note_id,
        }

    def _from_item(self, item: dict) -> Document:
        return Document(
            document_id=item["document_id"],
            tenant_id=item["tenant_id"],
            doc_type=item["doc_type"],
            status=DocumentStatus(item["status"]),
            serie=item["serie"],
            sequential=int(item["sequential"]),
            access_key=item["access_key"],
            client_id=item.get("client_id"),
            buyer_id_type=item["buyer_id_type"],
            buyer_id=item["buyer_id"],
            buyer_name=item["buyer_name"],
            buyer_email=item.get("buyer_email"),
            issued_at=date.fromisoformat(item["issued_at"]),
            sri_environment=item["sri_environment"],
            subtotal=Decimal(str(item["subtotal"])),
            total_discount=Decimal(str(item["total_discount"])),
            iva_15=Decimal(str(item["iva_15"])),
            iva_5=Decimal(str(item["iva_5"])),
            iva_0=Decimal(str(item.get("iva_0", "0.00"))),
            total=Decimal(str(item["total"])),
            payment_method=item.get("payment_method", "01"),
            lines=[InvoiceLine.from_dict(ln) for ln in item.get("lines", [])],
            retry_count=int(item.get("retry_count", 0)),
            deleted=bool(item.get("deleted", False)),
            created_at=_dt(item["created_at"]),
            updated_at=_dt(item["updated_at"]),
            created_by=item.get("created_by", ""),
            authorization_number=item.get("authorization_number"),
            authorized_at=_dt(item["authorized_at"]) if item.get("authorized_at") else None,
            rejected_at=_dt(item["rejected_at"]) if item.get("rejected_at") else None,
            xml_s3_key=item.get("xml_s3_key"),
            ride_s3_key=item.get("ride_s3_key"),
            sri_errors=item.get("sri_errors"),
            buyer_notification_status=BuyerNotificationStatus(item["buyer_notification_status"])
            if item.get("buyer_notification_status")
            else None,
            buyer_notified_at=_dt(item["buyer_notified_at"])
            if item.get("buyer_notified_at")
            else None,
            buyer_notification_error=item.get("buyer_notification_error"),
            annulled_at=_dt(item["annulled_at"]) if item.get("annulled_at") else None,
            annulled_by=item.get("annulled_by", ""),
            annulment_reason=item.get("annulment_reason"),
            related_document_id=item.get("related_document_id"),
            credit_note_reason=item.get("credit_note_reason"),
            manual_retry_count=int(item.get("manual_retry_count", 0)),
            retried_at=_dt(item["retried_at"]) if item.get("retried_at") else None,
            annulled_by_credit_note_id=item.get("annulled_by_credit_note_id"),
        )
