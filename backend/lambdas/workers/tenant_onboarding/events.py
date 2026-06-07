from dataclasses import dataclass

from shared.domain.events.domain_event import DomainEvent


@dataclass(frozen=True)
class OwnerCreatedEvent(DomainEvent):
    tenant_id:        str = ""
    email:            str = ""
    legal_rep_name: str = ""
    temp_password:    str = ""  # viaja cifrado en SQS SSE; nunca se loguea
