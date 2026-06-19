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

from datetime import UTC, date, datetime
from decimal import Decimal

from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

from lambdas._base.idempotency import IdempotencyContext, completion_transact_item, mark_completed
from lambdas.documents.domain.entities import (
    BuyerNotificationStatus,
    Document,
    DocumentStatus,
    InvoiceLine,
)
from lambdas.documents.domain.errors import DocumentNotFoundError
from lambdas.documents.domain.repositories.i_documents_repository import IDocumentsRepository
from shared.dates import current_ecuador_month_utc_bounds, now_utc
from shared.db.paginator import decode_cursor, encode_cursor
from shared.errors import DatabaseError
from shared.logger import get_logger

_log = get_logger(__name__)

_GSI = "tenant-docs-index"


def _dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


class DynamoDocumentsRepository(IDocumentsRepository):
    def __init__(self, table) -> None:
        self._table = table

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

    def list(
        self,
        tenant_id: str,
        *,
        status: str | None = None,
        serie: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 20,
        cursor: str | None = None,
    ) -> tuple[list[Document], str | None]:
        filters = [Attr("deleted").ne(True)]
        if status:
            filters.append(Attr("status").eq(status))
        if serie:
            filters.append(Attr("serie").eq(serie))
        if date_from:
            filters.append(Attr("issued_at").gte(date_from))
        if date_to:
            filters.append(Attr("issued_at").lte(date_to))

        filter_expr = filters[0]
        for f in filters[1:]:
            filter_expr = filter_expr & f

        kwargs: dict = {
            "IndexName": _GSI,
            "KeyConditionExpression": Key("tenant_id").eq(tenant_id),
            "FilterExpression": filter_expr,
            "ScanIndexForward": False,
            "Limit": limit,
        }
        start_key = decode_cursor(cursor)
        if start_key:
            kwargs["ExclusiveStartKey"] = start_key

        try:
            resp = self._table.query(**kwargs)
        except ClientError as exc:
            _log.error("DynamoDB query error (documents list)", error=str(exc))
            raise DatabaseError() from exc

        items = resp.get("Items", [])
        next_cursor = encode_cursor(resp.get("LastEvaluatedKey"))
        return [self._from_item(i) for i in items], next_cursor

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

    # ── write ─────────────────────────────────────────────────────────────────

    def save(
        self,
        document: Document,
        *,
        idempotency: IdempotencyContext | None = None,
        response: dict | None = None,
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
        )
