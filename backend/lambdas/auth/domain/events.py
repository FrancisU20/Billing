from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from shared.domain.events.domain_event import DomainEvent


@dataclass(frozen=True)
class PasswordResetRequestedEvent(DomainEvent):
    email: str = ""
    code: str = ""
    expires_at: datetime | None = None
