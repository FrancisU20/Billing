from __future__ import annotations

"""0004_update_plan_catalog — repricing + split Empresarial en Empresa/Corporativo.

Cambios de catalogo (precios/limites nuevos, ver tabla de producto):
- free/basic/pyme: reprecio y nuevos document_limit, sin cambio de self_service/api.
- pro: reprecio y nuevo document_limit + includes_api=False (acceso a API ahora
  es exclusivo de Empresa/Corporativo).
- enterprise (slug se mantiene, name -> "Empresa"): pasa a self_service=True con
  precio fijo y document_limit=5000 (ya no ilimitado); dedicated_queue=False (la
  cola dedicada se mueve al nuevo plan Corporativo, que reemplaza el rol de tope de
  gama que antes tenia Empresarial); includes_api se mantiene True.
- corporativo (nuevo): self_service=False (misma rama "lead capture" que usaba
  Empresarial), sin precio fijo ("Bajo medida" en frontend cuando monthly/annual
  price = 0 y self_service = False), document_limit ilimitado, dedicated_queue=True,
  includes_api=True.

Idempotente: si un plan ya tiene TODOS los valores nuevos (cada campo en
_UPDATES_BY_SLUG, no solo monthly_price — el plan "free" no cambia de precio
pero si de document_limit), se omite.
"""

from decimal import Decimal

from lambdas.plans.domain.commands import CreatePlanCommand, UpdatePlanCommand
from lambdas.plans.domain.errors import PlanNotFoundError, PlanSlugExistsError
from lambdas.plans.infra.plan_repository import DynamoPlanRepository
from lambdas.plans.use_cases.create_plan import CreatePlanUseCase
from migrations.context import MigrationContext, MigrationResult

MIGRATION_ID = "0004_update_plan_catalog"
DESCRIPTION = "Reprecio de catalogo de planes y split Empresarial en Empresa/Corporativo."

_UPDATES_BY_SLUG: dict[str, dict] = {
    "free": dict(
        monthly_price=Decimal("0.00"),
        annual_price=Decimal("0.00"),
        document_limit=10,
    ),
    "basic": dict(
        monthly_price=Decimal("9.99"),
        annual_price=Decimal("99.00"),
        document_limit=100,
    ),
    "pyme": dict(
        monthly_price=Decimal("24.99"),
        annual_price=Decimal("249.00"),
        document_limit=1000,
    ),
    "pro": dict(
        monthly_price=Decimal("39.99"),
        annual_price=Decimal("399.00"),
        document_limit=3000,
        includes_api=False,
    ),
    "enterprise": dict(
        name="Empresa",
        monthly_price=Decimal("69.99"),
        annual_price=Decimal("699.00"),
        document_limit=5000,
        self_service=True,
        dedicated_queue=False,
    ),
}

_CORPORATIVO = dict(
    slug="corporativo",
    name="Corporativo",
    description="Para distribuidoras y cadenas con alto volumen, a medida.",
    monthly_price=Decimal("0.00"),
    annual_price=Decimal("0.00"),
    document_limit=-1,
    limit_cycle="month",
    max_locations=-1,
    max_emission_points=-1,
    max_users=-1,
    pruebas_monthly_docs_limit=-1,
    pruebas_monthly_bulk_limit=-1,
    dedicated_queue=True,
    self_service=False,
    includes_credit_notes=True,
    includes_withholdings=True,
    includes_delivery_notes=True,
    includes_api=True,
    order=5,
)


def run(context: MigrationContext) -> MigrationResult:
    repo = DynamoPlanRepository(context.table("PLANS_TABLE"))
    updated = 0
    skipped = 0
    details: list[str] = []

    for slug, changes in _UPDATES_BY_SLUG.items():
        try:
            plan = repo.get_by_slug(slug)
        except PlanNotFoundError:
            skipped += 1
            details.append(f"skipped:{slug}:not_found")
            continue

        if all(getattr(plan, field) == value for field, value in changes.items()):
            skipped += 1
            details.append(f"skipped:{slug}:already_updated")
            continue

        cmd = UpdatePlanCommand(id=plan.id, updated_by=f"migration:{MIGRATION_ID}", **changes)
        plan.update(cmd)
        repo.commit(
            plan=plan,
            user_id=f"migration:{MIGRATION_ID}",
            action="UPDATE",
            idempotency=None,
            response=None,
        )
        updated += 1
        details.append(f"updated:{slug}:{plan.id}")

    try:
        existing = repo.get_by_slug(_CORPORATIVO["slug"])
        skipped += 1
        details.append(f"skipped:corporativo:{existing.id}:already_exists")
    except PlanNotFoundError:
        cmd = CreatePlanCommand(created_by=f"migration:{MIGRATION_ID}", **_CORPORATIVO)
        try:
            plan = CreatePlanUseCase(repo).execute(cmd)
            repo.commit(
                plan=plan,
                user_id=f"migration:{MIGRATION_ID}",
                action="CREATE",
                idempotency=None,
                response=None,
            )
            updated += 1
            details.append(f"created:{plan.slug}:{plan.id}")
        except PlanSlugExistsError:
            skipped += 1
            details.append("skipped:corporativo:already_exists")

    return MigrationResult(updated=updated, skipped=skipped, details=details)
