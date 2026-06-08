from __future__ import annotations

from enum import StrEnum


class SriEnvironment(StrEnum):
    TESTING = "testing"
    PRODUCTION = "production"


class TenantStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    INACTIVE = "inactive"


class PlanStatus(StrEnum):
    """Computed at read time from Tenant.plan_cycle_ends_at — never persisted.

    There is no "trial": every plan (including the free one) runs on a cycle
    (`Plan.limit_cycle`) with a document limit (`Plan.document_limit`). A plan
    is EXPIRED once its cycle ends — see Tenant.effective_plan_status().
    """

    ACTIVE = "active"
    EXPIRED = "expired"
