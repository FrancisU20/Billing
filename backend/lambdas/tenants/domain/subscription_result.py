from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SubscriptionActivationResult:
    tenant_id: str
    plan_cycle_ends_at: str
    subscription_status: str
