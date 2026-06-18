from __future__ import annotations

"""
DynamoDB implementation of ISequencesRepository.

Item schema in the sequences table (PK=TENANT#{tenant_id}):

  ESTAB items (sk = "ESTAB#{code}"):
    entity_type    : "ESTABLISHMENT"
    code           : "001"
    label          : "Matriz"
    tenant_id      : str
    emission_points: list[{code, label, initial_sequential}]
    version        : int
    created_at     : ISO-8601 str
    updated_at     : ISO-8601 str
    created_by     : str
    updated_by     : str

  SEQ items (sk = "SEQ#{estab}#{punto}"):
    entity_type    : "SEQUENCE"
    current        : int   (starts at initial_sequential - 1; first ADD 1 → initial_sequential)
    initial        : int   (initial_sequential value for this emission point)
"""

from datetime import UTC, datetime

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from lambdas._base.idempotency import IdempotencyContext, completion_transact_item, mark_completed
from lambdas.sequences.domain.entities import EmissionPoint, Establishment
from lambdas.sequences.domain.errors import (
    EstablishmentCodeExistsError,
    EstablishmentNotFoundError,
    SequenceExhaustedError,
)
from lambdas.sequences.domain.repositories.i_sequences_repository import ISequencesRepository
from shared.errors import DatabaseError, OptimisticLockError
from shared.logger import get_logger

_log = get_logger(__name__)

_MAX_SEQUENTIAL = 999_999_999


def _now() -> str:
    return datetime.now(UTC).isoformat()


class DynamoSequencesRepository(ISequencesRepository):
    def __init__(self, table) -> None:
        self._table = table

    # ── keys ──────────────────────────────────────────────────────────────────

    def _pk(self, tenant_id: str) -> str:
        return f"TENANT#{tenant_id}"

    def _estab_sk(self, code: str) -> str:
        return f"ESTAB#{code}"

    def _seq_sk(self, estab: str, punto: str) -> str:
        return f"SEQ#{estab}#{punto}"

    # ── read ──────────────────────────────────────────────────────────────────

    def find_establishment(self, tenant_id: str, code: str) -> Establishment | None:
        try:
            resp = self._table.get_item(Key={"pk": self._pk(tenant_id), "sk": self._estab_sk(code)})
            item = resp.get("Item")
            if not item:
                return None
            return self._from_item(item)
        except ClientError as exc:
            _log.error("DynamoDB get_item error (find_establishment)", error=str(exc))
            raise DatabaseError() from exc

    def get_establishment(self, tenant_id: str, code: str) -> Establishment:
        establishment = self.find_establishment(tenant_id, code)
        if establishment is None:
            raise EstablishmentNotFoundError()
        return establishment

    def list_establishments(self, tenant_id: str) -> list[Establishment]:
        try:
            resp = self._table.query(
                KeyConditionExpression=(
                    Key("pk").eq(self._pk(tenant_id)) & Key("sk").begins_with("ESTAB#")
                )
            )
            items = resp.get("Items", [])
            return sorted(
                [self._from_item(i) for i in items],
                key=lambda e: e.code,
            )
        except ClientError as exc:
            _log.error("DynamoDB query error (list_establishments)", error=str(exc))
            raise DatabaseError() from exc

    def has_sequence_started(self, tenant_id: str, serie: str) -> bool:
        estab, punto = serie[:3], serie[3:]
        try:
            resp = self._table.get_item(
                Key={"pk": self._pk(tenant_id), "sk": self._seq_sk(estab, punto)}
            )
            item = resp.get("Item")
            if not item:
                return False
            current = int(item.get("current", 0))
            initial = int(item.get("initial", 1))
            return current > (initial - 1)
        except ClientError as exc:
            _log.error("DynamoDB get_item error (has_sequence_started)", error=str(exc))
            raise DatabaseError() from exc

    def reserve_next(self, tenant_id: str, serie: str) -> int:
        estab, punto = serie[:3], serie[3:]
        try:
            resp = self._table.update_item(
                Key={"pk": self._pk(tenant_id), "sk": self._seq_sk(estab, punto)},
                UpdateExpression="ADD #cur :one",
                ConditionExpression="#cur < :max",
                ExpressionAttributeNames={"#cur": "current"},
                ExpressionAttributeValues={":one": 1, ":max": _MAX_SEQUENTIAL},
                ReturnValues="UPDATED_NEW",
            )
            return int(resp["Attributes"]["current"])
        except ClientError as exc:
            code = exc.response["Error"]["Code"]
            if code == "ConditionalCheckFailedException":
                raise SequenceExhaustedError(serie) from exc
            _log.error("DynamoDB update_item error (reserve_next)", error=str(exc))
            raise DatabaseError() from exc

    # ── write ─────────────────────────────────────────────────────────────────

    def commit(
        self,
        *,
        establishment: Establishment,
        action: str,
        user_id: str,
        new_emission_point: EmissionPoint | None = None,
        update_sequence: tuple[str, int] | None = None,
        idempotency: IdempotencyContext | None = None,
        response: dict | None = None,
    ) -> None:
        is_create = establishment.version == 1
        item = self._to_item(establishment)
        transact_items: list[dict] = []

        if is_create:
            transact_items.append(self._put_estab_create(establishment, item))
        else:
            transact_items.append(self._put_estab_update(establishment, item))

        if new_emission_point is not None:
            ep = new_emission_point
            # Determine the estab code by looking at the establishment code
            estab = establishment.code
            punto = ep.code
            transact_items.append(
                self._put_seq_init(
                    tenant_id=establishment.tenant_id,
                    estab=estab,
                    punto=punto,
                    initial=ep.initial_sequential,
                )
            )

        if update_sequence is not None:
            serie, new_initial = update_sequence
            estab, punto = serie[:3], serie[3:]
            transact_items.append(
                self._update_seq_reset(
                    tenant_id=establishment.tenant_id,
                    estab=estab,
                    punto=punto,
                    new_initial=new_initial,
                )
            )

        if idempotency is not None:
            if response is None:
                raise ValueError("response is required when idempotency context is provided")
            transact_items.append(completion_transact_item(idempotency, response))

        self._run_transaction(transact_items, idempotency=idempotency, is_create=is_create)

    def bootstrap_testing_point(self, tenant_id: str) -> None:
        pk = self._pk(tenant_id)
        now = _now()
        estab_item = {
            "pk": pk,
            "sk": self._estab_sk("001"),
            "entity_type": "ESTABLISHMENT",
            "code": "001",
            "label": "Matriz",
            "tenant_id": tenant_id,
            "emission_points": [{"code": "099", "label": "Pruebas", "initial_sequential": 1}],
            "version": 1,
            "created_at": now,
            "updated_at": now,
            "created_by": "system",
            "updated_by": "system",
        }
        seq_item = {
            "pk": pk,
            "sk": self._seq_sk("001", "099"),
            "entity_type": "SEQUENCE",
            "current": 0,
            "initial": 1,
        }

        for item in (estab_item, seq_item):
            try:
                self._table.put_item(
                    Item=item,
                    ConditionExpression="attribute_not_exists(pk)",
                )
            except ClientError as exc:
                if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                    continue
                _log.warning(
                    "bootstrap_testing_point: unexpected error (non-blocking)",
                    error=str(exc),
                    sk=item["sk"],
                )

    # ── helpers ───────────────────────────────────────────────────────────────

    def _put_estab_create(self, establishment: Establishment, item: dict) -> dict:
        return {
            "Put": {
                "TableName": self._table.table_name,
                "Item": item,
                "ConditionExpression": "attribute_not_exists(#pk)",
                "ExpressionAttributeNames": {"#pk": "pk"},
            }
        }

    def _put_estab_update(self, establishment: Establishment, item: dict) -> dict:
        return {
            "Put": {
                "TableName": self._table.table_name,
                "Item": item,
                "ConditionExpression": "attribute_exists(#pk) AND #version = :prev",
                "ExpressionAttributeNames": {"#pk": "pk", "#version": "version"},
                "ExpressionAttributeValues": {":prev": establishment.version - 1},
            }
        }

    def _put_seq_init(
        self,
        *,
        tenant_id: str,
        estab: str,
        punto: str,
        initial: int,
    ) -> dict:
        return {
            "Put": {
                "TableName": self._table.table_name,
                "Item": {
                    "pk": self._pk(tenant_id),
                    "sk": self._seq_sk(estab, punto),
                    "entity_type": "SEQUENCE",
                    "current": initial - 1,
                    "initial": initial,
                },
                "ConditionExpression": "attribute_not_exists(#pk)",
                "ExpressionAttributeNames": {"#pk": "pk"},
            }
        }

    def _update_seq_reset(
        self,
        *,
        tenant_id: str,
        estab: str,
        punto: str,
        new_initial: int,
    ) -> dict:
        return {
            "Update": {
                "TableName": self._table.table_name,
                "Key": {
                    "pk": self._pk(tenant_id),
                    "sk": self._seq_sk(estab, punto),
                },
                "UpdateExpression": "SET #cur = :new_cur, initial = :new_initial",
                "ExpressionAttributeNames": {"#cur": "current"},
                "ExpressionAttributeValues": {
                    ":new_cur": new_initial - 1,
                    ":new_initial": new_initial,
                },
            }
        }

    def _run_transaction(
        self,
        transact_items: list[dict],
        *,
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
                if is_create and reasons and reasons[0].get("code") == "ConditionalCheckFailed":
                    raise EstablishmentCodeExistsError() from exc
                raise OptimisticLockError() from exc
            _log.error("DynamoDB transact_write_items error", error=str(exc))
            raise DatabaseError() from exc

    # ── serialization ─────────────────────────────────────────────────────────

    def _to_item(self, establishment: Establishment) -> dict:
        return {
            "pk": self._pk(establishment.tenant_id),
            "sk": self._estab_sk(establishment.code),
            "entity_type": "ESTABLISHMENT",
            "code": establishment.code,
            "label": establishment.label,
            "tenant_id": establishment.tenant_id,
            "emission_points": [ep.to_dict() for ep in establishment.emission_points],
            "version": establishment.version,
            "created_at": establishment.created_at.isoformat(),
            "updated_at": establishment.updated_at.isoformat(),
            "created_by": establishment.created_by,
            "updated_by": establishment.updated_by,
        }

    def _from_item(self, item: dict) -> Establishment:
        return Establishment(
            code=item["code"],
            label=item["label"],
            tenant_id=item["tenant_id"],
            emission_points=[EmissionPoint.from_dict(ep) for ep in item.get("emission_points", [])],
            version=item.get("version", 1),
            created_at=datetime.fromisoformat(item["created_at"]),
            updated_at=datetime.fromisoformat(item["updated_at"]),
            created_by=item.get("created_by", ""),
            updated_by=item.get("updated_by", ""),
        )
