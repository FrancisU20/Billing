from __future__ import annotations

"""0003_backfill_onboarding_fields — campos nuevos de Tenant y Plan para onboarding.

Tenant.legal_name (razon social) y Tenant.accounting_required (obligado a llevar
contabilidad) son campos nuevos requeridos por el wizard de onboarding self-service.
Tenants creados antes de este cambio no los tienen: se backfillea
`legal_name = trade_name` (mejor valor disponible sin pedir datos al cliente) y
`accounting_required = False` (valor conservador, el tenant lo corrige despues si aplica).

Plan.pruebas_monthly_docs_limit, Plan.pruebas_monthly_bulk_limit, Plan.dedicated_queue y
Plan.self_service son campos nuevos que distinguen limites en sri_environment=pruebas y
la rama "lead capture" del plan Enterprise. Planes creados antes de este cambio se
backfillean con los mismos valores usados en el seed v0001 (ver ese archivo), indexados
por slug.
"""

from migrations.context import MigrationContext, MigrationResult

MIGRATION_ID = "0003_backfill_onboarding_fields"
DESCRIPTION = "Backfill Tenant.legal_name/accounting_required y campos pruebas_*/dedicated_queue/self_service de Plan."

_PLAN_DEFAULTS_BY_SLUG: dict[str, dict] = {
    "free": dict(
        pruebas_monthly_docs_limit=20,
        pruebas_monthly_bulk_limit=0,
        dedicated_queue=False,
        self_service=True,
    ),
    "basic": dict(
        pruebas_monthly_docs_limit=50,
        pruebas_monthly_bulk_limit=0,
        dedicated_queue=False,
        self_service=True,
    ),
    "pyme": dict(
        pruebas_monthly_docs_limit=200,
        pruebas_monthly_bulk_limit=50,
        dedicated_queue=False,
        self_service=True,
    ),
    "pro": dict(
        pruebas_monthly_docs_limit=500,
        pruebas_monthly_bulk_limit=200,
        dedicated_queue=False,
        self_service=True,
    ),
    "enterprise": dict(
        pruebas_monthly_docs_limit=-1,
        pruebas_monthly_bulk_limit=-1,
        dedicated_queue=True,
        self_service=False,
    ),
}


def _backfill_tenants(tenants_table) -> tuple[int, int, list[str]]:
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
            if "legal_name" in item and "accounting_required" in item:
                skipped += 1
                details.append(f"skipped:tenant:{tenant_id}:already_set")
                continue

            tenants_table.update_item(
                Key={"id": tenant_id},
                UpdateExpression="SET legal_name = :legal_name, accounting_required = :accounting_required",
                ExpressionAttributeValues={
                    ":legal_name": item.get("trade_name", ""),
                    ":accounting_required": False,
                },
            )
            updated += 1
            details.append(f"updated:tenant:{tenant_id}")

        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key

    return updated, skipped, details


def _backfill_plans(plans_table) -> tuple[int, int, list[str]]:
    updated = 0
    skipped = 0
    details: list[str] = []

    scan_kwargs: dict = {}
    while True:
        response = plans_table.scan(**scan_kwargs)
        for item in response.get("Items", []):
            if item.get("entity_type", "PLAN") != "PLAN":
                continue

            plan_id = item["id"]
            if "self_service" in item:
                skipped += 1
                details.append(f"skipped:plan:{plan_id}:already_set")
                continue

            defaults = _PLAN_DEFAULTS_BY_SLUG.get(item.get("slug", ""))
            if defaults is None:
                skipped += 1
                details.append(f"skipped:plan:{plan_id}:unknown_slug:{item.get('slug', '')}")
                continue

            plans_table.update_item(
                Key={"id": plan_id},
                UpdateExpression=(
                    "SET pruebas_monthly_docs_limit = :docs_limit, "
                    "pruebas_monthly_bulk_limit = :bulk_limit, "
                    "dedicated_queue = :dedicated_queue, "
                    "self_service = :self_service"
                ),
                ExpressionAttributeValues={
                    ":docs_limit": defaults["pruebas_monthly_docs_limit"],
                    ":bulk_limit": defaults["pruebas_monthly_bulk_limit"],
                    ":dedicated_queue": defaults["dedicated_queue"],
                    ":self_service": defaults["self_service"],
                },
            )
            updated += 1
            details.append(f"updated:plan:{plan_id}:{item.get('slug', '')}")

        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        scan_kwargs["ExclusiveStartKey"] = last_key

    return updated, skipped, details


def run(context: MigrationContext) -> MigrationResult:
    tenants_table = context.table("TENANTS_TABLE")
    plans_table = context.table("PLANS_TABLE")

    tenants_updated, tenants_skipped, tenant_details = _backfill_tenants(tenants_table)
    plans_updated, plans_skipped, plan_details = _backfill_plans(plans_table)

    return MigrationResult(
        updated=tenants_updated + plans_updated,
        skipped=tenants_skipped + plans_skipped,
        details=tenant_details + plan_details,
    )
