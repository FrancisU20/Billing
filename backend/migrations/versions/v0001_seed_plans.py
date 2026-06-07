from __future__ import annotations

"""0001_seed_plans — initial subscription plans."""

from decimal import Decimal

from lambdas.plans.domain.commands import CreatePlanCommand
from lambdas.plans.domain.errors import PlanSlugExistsError
from lambdas.plans.infra.plan_repository import DynamoPlanRepository
from lambdas.plans.use_cases.create_plan import CreatePlanUseCase
from migrations.context import MigrationContext, MigrationResult

MIGRATION_ID = "0001_seed_plans"
DESCRIPTION = "Seed initial subscription plans."

# Limits: -1 = unlimited. Free plan caps documents per YEAR; the rest per MONTH.
_PLANS: tuple[dict, ...] = (
    dict(
        slug="free",
        name="Gratis",
        description="Para profesionales independientes que facturan ocasionalmente.",
        monthly_price=Decimal("0.00"),
        annual_price=Decimal("0.00"),
        document_limit=20,
        limit_cycle="year",
        max_locations=1,
        max_emission_points=1,
        max_users=1,
        includes_credit_notes=False,
        includes_withholdings=False,
        includes_delivery_notes=False,
        includes_api=False,
        order=0,
    ),
    dict(
        slug="basic",
        name="Básico",
        description="Para negocios que arrancan con facturación electrónica.",
        monthly_price=Decimal("5.99"),
        annual_price=Decimal("57.00"),
        document_limit=50,
        limit_cycle="month",
        max_locations=1,
        max_emission_points=2,
        max_users=2,
        includes_credit_notes=True,
        includes_withholdings=True,
        includes_delivery_notes=True,
        includes_api=False,
        order=1,
    ),
    dict(
        slug="pyme",
        name="Pyme",
        description="Para pymes en crecimiento con varios locales.",
        monthly_price=Decimal("14.99"),
        annual_price=Decimal("143.00"),
        document_limit=300,
        limit_cycle="month",
        max_locations=3,
        max_emission_points=5,
        max_users=5,
        includes_credit_notes=True,
        includes_withholdings=True,
        includes_delivery_notes=True,
        includes_api=False,
        order=2,
    ),
    dict(
        slug="pro",
        name="Profesional",
        description="Para empresas con integración contable y multi-establecimiento.",
        monthly_price=Decimal("29.99"),
        annual_price=Decimal("287.00"),
        document_limit=1000,
        limit_cycle="month",
        max_locations=-1,
        max_emission_points=-1,
        max_users=10,
        includes_credit_notes=True,
        includes_withholdings=True,
        includes_delivery_notes=True,
        includes_api=True,
        order=3,
    ),
    dict(
        slug="enterprise",
        name="Empresarial",
        description="Para distribuidoras y cadenas con alto volumen.",
        monthly_price=Decimal("59.99"),
        annual_price=Decimal("575.00"),
        document_limit=-1,
        limit_cycle="month",
        max_locations=-1,
        max_emission_points=-1,
        max_users=-1,
        includes_credit_notes=True,
        includes_withholdings=True,
        includes_delivery_notes=True,
        includes_api=True,
        order=4,
    ),
)


def run(context: MigrationContext) -> MigrationResult:
    repo = DynamoPlanRepository(context.table("PLANS_TABLE"))
    use_case = CreatePlanUseCase(repo)
    created = 0
    skipped = 0
    details: list[str] = []

    for spec in _PLANS:
        cmd = CreatePlanCommand(created_by=f"migration:{MIGRATION_ID}", **spec)
        try:
            plan = use_case.execute(cmd)
            repo.commit(
                plan=plan,
                user_id=f"migration:{MIGRATION_ID}",
                action="CREATE",
                idempotency=None,
                response=None,
            )
            created += 1
            details.append(f"created:{plan.slug}:{plan.id}")
        except PlanSlugExistsError:
            skipped += 1
            details.append(f"skipped:{spec['slug']}:already_exists")

    return MigrationResult(created=created, skipped=skipped, details=details)
