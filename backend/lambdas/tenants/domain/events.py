from dataclasses import dataclass
from shared.domain.events.domain_event import DomainEvent


@dataclass(frozen=True)
class TenantCreatedEvent(DomainEvent):
    tenant_id:        str = ""
    ruc:              str = ""
    email:            str = ""
    nombre_rep_legal: str = ""   # para el email de bienvenida con Brevo


@dataclass(frozen=True)
class TenantUpdatedEvent(DomainEvent):
    tenant_id:  str = ""
    updated_by: str = ""


@dataclass(frozen=True)
class TenantStatusChangedEvent(DomainEvent):
    tenant_id:    str = ""
    nuevo_estado: str = ""
    updated_by:   str = ""


@dataclass(frozen=True)
class TenantDeletedEvent(DomainEvent):
    tenant_id:  str = ""
    deleted_by: str = ""
