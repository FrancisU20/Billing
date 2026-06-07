from __future__ import annotations

from enum import Enum


class SriEnvironment(str, Enum):
    TESTING = "testing"
    PRODUCTION = "production"


class TenantStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    INACTIVE = "inactive"


class PlanStatus(str, Enum):
    ACTIVE = "active"  # plan current and paid
    TRIAL = "trial"  # trial period active
    EXPIRED = "expired"  # payment overdue / expired
    CANCELLED = "cancelled"  # cancelled by tenant or system
