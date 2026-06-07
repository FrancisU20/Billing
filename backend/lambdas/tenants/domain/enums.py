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
    ACTIVE = "active"  # plan current and paid
    TRIAL = "trial"  # trial period active
    EXPIRED = "expired"  # payment overdue / expired
    CANCELLED = "cancelled"  # cancelled by tenant or system
