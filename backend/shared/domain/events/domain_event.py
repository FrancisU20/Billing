"""
Base domain event.

Use cases emit DomainEvents instead of publishing directly to SQS.
This decouples the domain from the messaging infrastructure.

handler.py is responsible for publishing events after the use case
completes — the domain does not know SQS exists.

Naming convention: <Entity><Action>Event  (TenantCreatedEvent, InvoiceEmittedEvent)
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


@dataclass(frozen=True)
class DomainEvent:
    event_id:    str      = field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def event_type(self) -> str:
        """Event name — used as the MessageAttribute in SQS."""
        return self.__class__.__name__
