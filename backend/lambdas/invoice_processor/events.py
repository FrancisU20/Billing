from __future__ import annotations

from dataclasses import dataclass

from shared.domain.events.domain_event import DomainEvent


@dataclass(frozen=True)
class DocumentAuthorizedEvent(DomainEvent):
    tenant_id: str = ""
    document_id: str = ""
    access_key: str = ""
    authorization_number: str = ""
    tenant_email: str = ""
    legal_rep_name: str = ""


@dataclass(frozen=True)
class DocumentRejectedEvent(DomainEvent):
    tenant_id: str = ""
    document_id: str = ""
    access_key: str = ""
    tenant_email: str = ""
    legal_rep_name: str = ""
    sri_errors: list[dict] | None = None


@dataclass(frozen=True)
class DocumentFailedPermanentEvent(DomainEvent):
    tenant_id: str = ""
    document_id: str = ""
    access_key: str = ""
    tenant_email: str = ""
    legal_rep_name: str = ""


@dataclass(frozen=True)
class DocumentBuyerNotificationRequestedEvent(DomainEvent):
    tenant_id: str = ""
    document_id: str = ""
