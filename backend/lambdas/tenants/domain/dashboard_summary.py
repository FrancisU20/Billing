from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class TopPlanSummary:
    plan_id: str
    name: str
    tenant_count: int

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "name": self.name,
            "tenant_count": self.tenant_count,
        }


@dataclass(frozen=True)
class RecentTenant:
    id: str
    trade_name: str
    created_at: str

    def to_dict(self) -> dict:
        return {"id": self.id, "trade_name": self.trade_name, "created_at": self.created_at}


@dataclass(frozen=True)
class DailyRevenuePoint:
    date: str
    amount: Decimal

    def to_dict(self) -> dict:
        return {"date": self.date, "amount": str(self.amount)}


@dataclass(frozen=True)
class SuperadminDashboardSummary:
    generated_at: str
    tenants_total: int
    tenants_new_this_month: int
    tenants_new_this_month_trend_pct: Decimal | None
    tenants_by_environment: dict[str, int]
    memberships_active: int
    memberships_inactive: int
    revenue_this_month: Decimal
    revenue_this_month_trend_pct: Decimal | None
    revenue_this_year: Decimal
    revenue_this_year_trend_pct: Decimal | None
    mrr_estimate: Decimal
    top_plan: TopPlanSummary | None
    daily_revenue: list[DailyRevenuePoint]
    recent_tenants: list[RecentTenant]

    def to_dict(self) -> dict:
        return {
            "generated_at": self.generated_at,
            "tenants_total": self.tenants_total,
            "tenants_new_this_month": self.tenants_new_this_month,
            "tenants_new_this_month_trend_pct": _opt_str(self.tenants_new_this_month_trend_pct),
            "tenants_by_environment": self.tenants_by_environment,
            "memberships_active": self.memberships_active,
            "memberships_inactive": self.memberships_inactive,
            "revenue_this_month": str(self.revenue_this_month),
            "revenue_this_month_trend_pct": _opt_str(self.revenue_this_month_trend_pct),
            "revenue_this_year": str(self.revenue_this_year),
            "revenue_this_year_trend_pct": _opt_str(self.revenue_this_year_trend_pct),
            "mrr_estimate": str(self.mrr_estimate),
            "top_plan": self.top_plan.to_dict() if self.top_plan else None,
            "daily_revenue": [point.to_dict() for point in self.daily_revenue],
            "recent_tenants": [tenant.to_dict() for tenant in self.recent_tenants],
        }


def _opt_str(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


@dataclass(frozen=True)
class TenantAggregateStats:
    """Resultado de un unico Scan de la tabla tenants (ver
    DynamoTenantRepository.aggregate_dashboard_stats)."""

    total: int
    new_this_month: int
    new_previous_month: int
    by_environment: dict[str, int]
    by_subscription_status: dict[str, int]
    active_by_plan_id: dict[str, int]
    recent_tenants: list[RecentTenant]


@dataclass(frozen=True)
class PaymentRevenueStats:
    """Resultado de un unico Scan de la tabla payments (ver
    DynamoPaymentReader.aggregate_revenue)."""

    gross_this_month: Decimal
    gross_previous_month: Decimal
    gross_this_year: Decimal
    gross_previous_year: Decimal
    daily_last_30_days: list[DailyRevenuePoint]

    @classmethod
    def empty(cls) -> PaymentRevenueStats:
        return cls(
            gross_this_month=Decimal("0.00"),
            gross_previous_month=Decimal("0.00"),
            gross_this_year=Decimal("0.00"),
            gross_previous_year=Decimal("0.00"),
            daily_last_30_days=[],
        )


@dataclass(frozen=True)
class PlanPricing:
    name: str
    monthly_price: Decimal
    annual_price: Decimal
    limit_cycle: str
