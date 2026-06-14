from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from shared.domain.events.domain_event import DomainEvent


@dataclass(frozen=True)
class EnterpriseLeadCreatedEvent(DomainEvent):
    lead_id: str = ""
    ruc: str = ""
    trade_name: str = ""
    email: str = ""
    plan_id: str = ""


@dataclass(frozen=True)
class OnboardingOtpRequestedEvent(DomainEvent):
    verification_id: str = ""
    ruc: str = ""
    email: str = ""
    legal_rep_name: str = ""
    otp: str = ""
    expires_at: datetime | None = None
