from __future__ import annotations

from dataclasses import dataclass

from botocore.exceptions import ClientError

from shared.errors import DatabaseError, ValidationError
from shared.logger import get_logger

_log = get_logger(__name__)


@dataclass
class PlanInfo:
    document_limit: int
    pruebas_monthly_docs_limit: int


class DynamoPlanReader:
    """Reads only the billing-relevant fields from the plans table.

    Intentionally does not import lambdas.plans.* to keep lambda bundles independent.
    """

    def __init__(self, plans_table) -> None:
        self._table = plans_table

    def get(self, plan_id: str) -> PlanInfo:
        try:
            resp = self._table.get_item(Key={"id": plan_id})
        except ClientError as exc:
            _log.error("DynamoDB get_item error (plan_reader)", error=str(exc))
            raise DatabaseError() from exc

        item = resp.get("Item")
        if not item or not item.get("active", True):
            raise ValidationError("plan_id inválido o inactivo")

        return PlanInfo(
            document_limit=int(item.get("document_limit", 0)),
            pruebas_monthly_docs_limit=int(item.get("pruebas_monthly_docs_limit", 0)),
        )
