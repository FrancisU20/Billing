"""
Evento de dominio base.

Los use cases emiten DomainEvents en lugar de publicar directamente a SQS.
Esto desacopla el dominio de la infraestructura de mensajería.

El handler.py es el responsable de publicar los eventos después de que
el use case completa — el dominio no sabe que existe SQS.

Convención de nombres: <Entidad><Acción>Event  (TenantCreatedEvent, InvoiceEmittedEvent)
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
        """Nombre del evento — se usa como MessageAttribute en SQS."""
        return self.__class__.__name__
