from __future__ import annotations

"""
DynamoDB implementation of the Client repository.

PK/SK:
    pk = TENANT#{tenant_id}
    sk = CLIENT#{client_id}

Identification lock:
    pk = TENANT#{tenant_id}
    sk = CLIENT_IDENTIFICATION#{identification}

The lock is active only while the client is not soft-deleted. Deletes remove
the lock in the same transaction, so a deleted identification can be reused.
"""

from datetime import datetime

from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

from lambdas._base.idempotency import (
    IdempotencyContext,
    completion_transact_item,
    mark_completed,
)
from lambdas.clients.domain.entity import Client
from lambdas.clients.domain.enums import ClientStatus, IdentificationType, PersonType
from lambdas.clients.domain.errors import (
    ClientDuplicateIdentificationError,
    ClientNotFoundError,
)
from lambdas.clients.domain.repositories.i_client_repository import IClientRepository
from lambdas.clients.domain.value_objects.address import Address
from shared.audit.writer import audit_item, audit_put_transact_item
from shared.db.base_repository import BaseRepository
from shared.errors import DatabaseError, OptimisticLockError
from shared.logger import get_logger

_log = get_logger(__name__)


class DynamoClientRepository(BaseRepository, IClientRepository):
    _prefix = "CLIENT"
    _lock_prefix = "CLIENT_IDENTIFICATION"

    def get_by_id(self, client_id: str) -> Client:
        item = self._get_raw(client_id)
        if not item:
            raise ClientNotFoundError()
        return self._from_item(item)

    def get_by_identification(
        self,
        identification: str,
        exclude_id: str | None = None,
    ) -> Client | None:
        try:
            response = self._table.query(
                IndexName="identification-index",
                KeyConditionExpression=(
                    Key("tenant_id").eq(self._tenant_id) & Key("identification").eq(identification)
                ),
            )
        except ClientError as exc:
            _log.error("DynamoDB identification-index query error", error=str(exc))
            raise DatabaseError() from exc

        for item in response.get("Items", []):
            if item.get("entity_type") != "CLIENT" or item.get("deleted"):
                continue
            if exclude_id and item.get("id") == exclude_id:
                continue
            return self._from_item(item)
        return None

    def list(
        self,
        limit: int,
        next_token: str | None,
        status: str | None = None,
        q: str | None = None,
        identification: str | None = None,
        identification_type: str | None = None,
        created_from: str | None = None,
        created_to: str | None = None,
    ) -> tuple[list[Client], str | None]:
        filters = _ClientListFilters(
            status=status,
            q=q,
            identification_type=identification_type,
            created_from=created_from,
            created_to=created_to,
        )
        if identification:
            client = self.get_by_identification(identification.strip().upper())
            if not client:
                return [], None
            if not filters.matches(client):
                return [], None
            return [client], None

        extra_filter = filters.to_dynamo_filter()

        cursor = next_token
        clients: list[Client] = []
        while len(clients) < limit:
            items, cursor = self._list_raw(
                limit=limit - len(clients),
                next_token=cursor,
                extra_filter=extra_filter,
            )
            for item in items:
                client = self._from_item(item)
                if not filters.matches(client):
                    continue
                clients.append(client)
            if cursor is None:
                break
        return clients, cursor

    def save(self, client: Client, user_id: str) -> None:
        self.commit(
            client=client,
            user_id=user_id,
            action="SAVE",
            idempotency=None,
            response=None,
        )

    def commit(
        self,
        *,
        client: Client,
        user_id: str,
        action: str,
        idempotency: IdempotencyContext | None,
        response: dict | None,
    ) -> None:
        item = self._to_item(client)
        old_raw = self._raw_by_key(client.id)
        is_create = old_raw is None and client.version == 1
        transact_items: list[dict] = []

        if is_create:
            transact_items.extend(self._create_items(client, item))
        else:
            transact_items.extend(self._update_items(client, item, old_raw))

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
                        entity_type="CLIENT",
                        entity_id=client.id,
                        action=action,
                        changed_by=user_id,
                        before=old_raw,
                        after=item,
                    ),
                )
            )

        self._transact_write(transact_items, idempotency, is_create)

    def _raw_by_key(self, client_id: str) -> dict | None:
        try:
            response = self._table.get_item(Key={"pk": self._pk(), "sk": self._sk(client_id)})
            return response.get("Item")
        except ClientError as exc:
            _log.error("DynamoDB get_item error", error=str(exc))
            raise DatabaseError() from exc

    def _create_items(self, client: Client, item: dict) -> list[dict]:
        return [
            {
                "Put": {
                    "TableName": self._table.table_name,
                    "Item": self._identification_lock_item(client),
                    "ConditionExpression": "attribute_not_exists(#pk)",
                    "ExpressionAttributeNames": {"#pk": "pk"},
                }
            },
            {
                "Put": {
                    "TableName": self._table.table_name,
                    "Item": item,
                    "ConditionExpression": "attribute_not_exists(#pk)",
                    "ExpressionAttributeNames": {"#pk": "pk"},
                }
            },
        ]

    def _update_items(self, client: Client, item: dict, old_raw: dict | None) -> list[dict]:
        if old_raw is None:
            raise ClientNotFoundError()

        items: list[dict] = []
        old_identification = old_raw.get("identification")
        identification_changed = old_identification != client.identification

        if identification_changed and not client.deleted:
            items.append(self._put_lock_item(client))
            if old_identification:
                items.append(self._delete_lock_item(old_identification, client.id))
        elif client.deleted and old_identification:
            items.append(self._delete_lock_item(old_identification, client.id))

        items.append(
            {
                "Put": {
                    "TableName": self._table.table_name,
                    "Item": item,
                    "ConditionExpression": "attribute_exists(#pk) AND #version = :prev",
                    "ExpressionAttributeNames": {"#pk": "pk", "#version": "version"},
                    "ExpressionAttributeValues": {":prev": client.version - 1},
                }
            }
        )
        return items

    def _put_lock_item(self, client: Client) -> dict:
        return {
            "Put": {
                "TableName": self._table.table_name,
                "Item": self._identification_lock_item(client),
                "ConditionExpression": "attribute_not_exists(#pk)",
                "ExpressionAttributeNames": {"#pk": "pk"},
            }
        }

    def _delete_lock_item(self, identification: str, client_id: str) -> dict:
        return {
            "Delete": {
                "TableName": self._table.table_name,
                "Key": {"pk": self._pk(), "sk": self._lock_sk(identification)},
                "ConditionExpression": "attribute_not_exists(#pk) OR #client_id = :client_id",
                "ExpressionAttributeNames": {"#pk": "pk", "#client_id": "client_id"},
                "ExpressionAttributeValues": {":client_id": client_id},
            }
        }

    def _transact_write(
        self,
        transact_items: list[dict],
        idempotency: IdempotencyContext | None,
        is_create: bool,
    ) -> None:
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
                    "DynamoDB transact_write_items cancelled",
                    is_create=is_create,
                    reasons=reasons,
                )
                if self._identification_lock_failed(transact_items, reasons, is_create):
                    raise ClientDuplicateIdentificationError() from exc
                raise OptimisticLockError() from exc
            _log.error("DynamoDB transact_write_items error", error=str(exc))
            raise DatabaseError() from exc

    def _identification_lock_failed(
        self,
        transact_items: list[dict],
        reasons: list[dict],
        is_create: bool,
    ) -> bool:
        if not reasons:
            return is_create
        for index, reason in enumerate(reasons):
            if reason.get("code") != "ConditionalCheckFailed":
                continue
            if index >= len(transact_items):
                continue
            operation = transact_items[index]
            put = operation.get("Put")
            if put and put.get("Item", {}).get("entity_type") == "CLIENT_IDENTIFICATION_LOCK":
                return True
        return False

    def _lock_sk(self, identification: str) -> str:
        return f"{self._lock_prefix}#{identification}"

    def _identification_lock_item(self, client: Client) -> dict:
        return {
            "pk": self._pk(),
            "sk": self._lock_sk(client.identification),
            "entity_type": "CLIENT_IDENTIFICATION_LOCK",
            "client_id": client.id,
            "locked_identification": client.identification,
            "created_at": client.created_at.isoformat(),
            "created_by": client.created_by,
        }

    def _to_item(self, client: Client) -> dict:
        return {
            "entity_type": "CLIENT",
            "pk": self._pk(),
            "sk": self._sk(client.id),
            "id": client.id,
            "tenant_id": client.tenant_id,
            "identification": client.identification,
            "identification_type": client.identification_type.value,
            "person_type": client.person_type.value,
            "legal_name": client.legal_name,
            "trade_name": client.trade_name,
            "special_taxpayer": client.special_taxpayer,
            "emails": client.emails,
            "phones": client.phones,
            "addresses": [a.to_dict() for a in client.addresses],
            "status": client.status.value,
            "version": client.version,
            "deleted": client.deleted,
            "created_at": client.created_at.isoformat(),
            "updated_at": client.updated_at.isoformat(),
            "created_by": client.created_by,
            "updated_by": client.updated_by,
            "deleted_at": client.deleted_at.isoformat() if client.deleted_at else None,
            "deleted_by": client.deleted_by,
        }

    def _from_item(self, item: dict) -> Client:
        return Client(
            id=item["id"],
            tenant_id=item["tenant_id"],
            identification=item["identification"],
            identification_type=IdentificationType(item.get("identification_type", "ruc")),
            person_type=PersonType(item.get("person_type", "natural")),
            legal_name=item["legal_name"],
            trade_name=item.get("trade_name", ""),
            special_taxpayer=item.get("special_taxpayer", False),
            emails=list(item.get("emails", [])),
            phones=list(item.get("phones", [])),
            addresses=[Address.from_dict(a) for a in item.get("addresses", [])],
            status=ClientStatus(item.get("status", "active")),
            version=item.get("version", 1),
            deleted=item.get("deleted", False),
            created_at=datetime.fromisoformat(item["created_at"]),
            updated_at=datetime.fromisoformat(item["updated_at"]),
            created_by=item.get("created_by", ""),
            updated_by=item.get("updated_by", ""),
            deleted_at=datetime.fromisoformat(item["deleted_at"])
            if item.get("deleted_at")
            else None,
            deleted_by=item.get("deleted_by"),
        )


class _ClientListFilters:
    def __init__(
        self,
        *,
        status: str | None,
        q: str | None,
        identification_type: str | None,
        created_from: str | None,
        created_to: str | None,
    ) -> None:
        self.status = status
        self.needle = q.strip().lower() if q else ""
        self.identification_type = identification_type
        self.created_from = created_from
        self.created_to = created_to

    def to_dynamo_filter(self):
        filter_expr = Attr("entity_type").eq("CLIENT")
        if self.status:
            filter_expr = filter_expr & Attr("status").eq(self.status)
        if self.identification_type:
            filter_expr = filter_expr & Attr("identification_type").eq(self.identification_type)
        if self.created_from:
            filter_expr = filter_expr & Attr("created_at").gte(self.created_from)
        if self.created_to:
            filter_expr = filter_expr & Attr("created_at").lte(self.created_to)
        return filter_expr

    def matches(self, client: Client) -> bool:
        if self.status and client.status.value != self.status:
            return False
        if (
            self.identification_type
            and client.identification_type.value != self.identification_type
        ):
            return False
        created_at = client.created_at.isoformat()
        if self.created_from and created_at < self.created_from:
            return False
        if self.created_to and created_at > self.created_to:
            return False
        if not self.needle:
            return True
        return (
            self.needle in client.legal_name.lower()
            or self.needle in client.trade_name.lower()
            or self.needle in client.identification.lower()
        )
