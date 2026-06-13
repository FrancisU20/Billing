from __future__ import annotations

from dataclasses import dataclass

from shared.domain.events.domain_event import DomainEvent


@dataclass(frozen=True)
class EnterpriseLeadCreatedEvent(DomainEvent):
    lead_id: str = ""
    ruc: str = ""
    trade_name: str = ""
    email: str = ""
    plan_id: str = ""
