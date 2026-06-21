from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from lambdas.tenants.domain.dashboard_summary import (
    PaymentRevenueStats,
    PlanPricing,
    SuperadminDashboardSummary,
    TopPlanSummary,
)
from lambdas.tenants.domain.repositories.i_payment_reader import IPaymentReader
from lambdas.tenants.domain.repositories.i_plan_catalog import IPlanCatalog
from lambdas.tenants.domain.repositories.i_tenant_repository import ITenantRepository
from shared.billing import gross_price
from shared.dates import to_ecuador


class GetSuperadminDashboardUseCase:
    """Agrega estadisticas globales para el dashboard superadmin a partir de 3 fuentes
    de solo lectura (tenants, payments, plans) — ver context/TENANTS.md."""

    def __init__(
        self,
        tenant_repo: ITenantRepository,
        payment_reader: IPaymentReader | None,
        plan_catalog: IPlanCatalog,
    ) -> None:
        self._tenant_repo = tenant_repo
        self._payment_reader = payment_reader
        self._plan_catalog = plan_catalog

    def execute(self, now: datetime) -> SuperadminDashboardSummary:
        tenant_stats = self._tenant_repo.aggregate_dashboard_stats(now)
        revenue_stats = (
            self._payment_reader.aggregate_revenue(now)
            if self._payment_reader
            else PaymentRevenueStats.empty()
        )
        pricing = self._plan_catalog.get_pricing(set(tenant_stats.active_by_plan_id))

        return SuperadminDashboardSummary(
            generated_at=to_ecuador(now).isoformat(),
            tenants_total=tenant_stats.total,
            tenants_new_this_month=tenant_stats.new_this_month,
            tenants_new_this_month_trend_pct=self._trend_pct(
                tenant_stats.new_this_month, tenant_stats.new_previous_month
            ),
            tenants_by_environment=tenant_stats.by_environment,
            memberships_active=tenant_stats.by_subscription_status.get("active", 0),
            memberships_inactive=tenant_stats.total
            - tenant_stats.by_subscription_status.get("active", 0),
            revenue_this_month=revenue_stats.gross_this_month,
            revenue_this_month_trend_pct=self._trend_pct(
                revenue_stats.gross_this_month, revenue_stats.gross_previous_month
            ),
            revenue_this_year=revenue_stats.gross_this_year,
            revenue_this_year_trend_pct=self._trend_pct(
                revenue_stats.gross_this_year, revenue_stats.gross_previous_year
            ),
            mrr_estimate=self._mrr_estimate(tenant_stats.active_by_plan_id, pricing),
            top_plan=self._top_plan(tenant_stats.active_by_plan_id, pricing),
            daily_revenue=revenue_stats.daily_last_30_days,
            recent_tenants=tenant_stats.recent_tenants,
        )

    @staticmethod
    def _trend_pct(current: Decimal | int, previous: Decimal | int) -> Decimal | None:
        """% de variacion vs el periodo anterior. `None` (no `0%`) cuando el periodo
        anterior fue 0 — no hay un "% de crecimiento" honesto contra una base de cero,
        y mostrar 0% insinuaria falsamente "sin cambios"."""
        previous_decimal = Decimal(previous)
        if previous_decimal == 0:
            return None
        current_decimal = Decimal(current)
        pct = (current_decimal - previous_decimal) / previous_decimal * 100
        return pct.quantize(Decimal("0.1"))

    @staticmethod
    def _mrr_estimate(
        active_by_plan_id: dict[str, int], pricing: dict[str, PlanPricing]
    ) -> Decimal:
        total = Decimal("0.00")
        for plan_id, tenant_count in active_by_plan_id.items():
            plan = pricing.get(plan_id)
            if not plan:
                continue
            monthly_equivalent = (
                plan.monthly_price if plan.limit_cycle == "month" else plan.annual_price / 12
            )
            total += Decimal(gross_price(str(monthly_equivalent))) * tenant_count
        return total

    @staticmethod
    def _top_plan(
        active_by_plan_id: dict[str, int], pricing: dict[str, PlanPricing]
    ) -> TopPlanSummary | None:
        if not active_by_plan_id:
            return None
        plan_id, tenant_count = max(active_by_plan_id.items(), key=lambda kv: kv[1])
        plan = pricing.get(plan_id)
        return TopPlanSummary(
            plan_id=plan_id,
            name=plan.name if plan else plan_id,
            tenant_count=tenant_count,
        )
