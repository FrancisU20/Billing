from __future__ import annotations

from botocore.exceptions import ClientError

from lambdas.tenants.domain.repositories.i_plan_catalog import IPlanCatalog
from shared.errors import DatabaseError, ValidationError
from shared.logger import get_logger

_log = get_logger(__name__)


class DynamoPlanCatalog(IPlanCatalog):
    """
    Validates plan existence and status directly against the plans table.
    Intentionally does NOT import from lambdas.plans.* to keep lambda
    bundles independent.
    """

    def __init__(self, plans_table) -> None:
        self._table = plans_table

    def ensure_active(self, plan_id: str) -> None:
        if not plan_id:
            raise ValidationError("plan_id es requerido")

        try:
            resp = self._table.get_item(Key={"id": plan_id})
        except ClientError as exc:
            _log.error("DynamoDB get_item error (plan catalog)", error=str(exc))
            raise DatabaseError()

        item = resp.get("Item")
        if not item or item.get("entity_type", "PLAN") != "PLAN":
            raise ValidationError("plan_id inválido")

        if item.get("deleted"):
            raise ValidationError("plan_id inválido")

        if not item.get("active", True):
            raise ValidationError("plan_id no está activo")
