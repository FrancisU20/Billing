from __future__ import annotations

"""0002_backfill_plan_cycle_ends_at — fecha de fin de ciclo del plan por tenant.

`Tenant.plan_cycle_ends_at` reemplaza al campo muerto `trial_ends_at` (siempre
`None` — nunca existió un flujo de "trial"). Tenants creados antes de este
cambio no tienen el valor; se calcula igual que en `Tenant.create()`:
`created_at + 1 año` (planes con limit_cycle="year") o `+ 1 mes` ("month").

Es la base del estado de plan calculado (`Tenant.effective_plan_status`) — sin
esta fecha, esos tenants legacy aparecerían siempre como "active" sin importar
cuánto tiempo lleven con el plan.
"""

from datetime import datetime

from dateutil.relativedelta import relativedelta

from migrations.context import MigrationContext, MigrationResult

MIGRATION_ID = "0002_backfill_plan_cycle_ends_at"
DESCRIPTION = "Backfill Tenant.plan_cycle_ends_at desde created_at + limit_cycle del plan."


def _cycle_duration(limit_cycle: str) -> relativedelta:
    return relativedelta(years=1) if limit_cycle == "year" else relativedelta(months=1)


def _plan_limit_cycle(plans_table, plan_id: str) -> str:
    """Lee limit_cycle directo de la tabla de planes — sin importar lambdas.plans.*."""
    if not plan_id:
        return "month"
    item = plans_table.get_item(Key={"id": plan_id}).get("Item")
    return item.get("limit_cycle", "month") if item else "month"


def run(context: MigrationContext) -> MigrationResult:
    tenants_table = context.table("TENANTS_TABLE")
    plans_table = context.table("PLANS_TABLE")

    updated = 0
    skipped = 0
    details: list[str] = []

    scan_kwargs: dict = {}
    while True:
        response = tenants_table.scan(**scan_kwargs)
        for item in response.get("Items", []):
            if item.get("entity_type") != "TENANT":
                continue

            tenant_id = item["id"]
            if item.get("plan_cycle_ends_at"):
                skipped += 1
                details.append(f"skipped:{tenant_id}:already_set")
                continue

            limit_cycle = _plan_limit_cycle(plans_table, item.get("plan_id", ""))
            created_at = datetime.fromisoformat(item["created_at"])
            plan_cycle_ends_at = (created_at + _cycle_duration(limit_cycle)).isoformat()

            tenants_table.update_item(
                Key={"id": tenant_id},
                UpdateExpression="SET plan_cycle_ends_at = :value",
                ExpressionAttributeValues={":value": plan_cycle_ends_at},
            )
            updated += 1
            details.append(f"updated:{tenant_id}:{plan_cycle_ends_at}")

        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key

    return MigrationResult(updated=updated, skipped=skipped, details=details)
