from __future__ import annotations

"""Application ports for invoice_processor.

`IDocumentsRepository` (documents lambda) and `DynamoTenantRepository` (tenants
lambda) are reused directly — same pattern already used by `documents/handler.py`
("acceso directo controlado" per BACKEND.md, since every Lambda shares the same
deployed code asset). Only the genuinely external integrations (SRI SOAP, S3, SQS)
get a port here, so use cases stay testable with fakes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from shared.domain.events.domain_event import DomainEvent


@dataclass(frozen=True)
class SriErrorDetail:
    code: str
    message: str
    additional_info: str | None = None

    def to_dict(self) -> dict:
        from lambdas.invoice_processor.sri_error_mapper import normalize_sri_error

        return normalize_sri_error(
            code=self.code,
            message=self.message,
            additional_info=self.additional_info,
        )


@dataclass(frozen=True)
class RecepcionResult:
    received: bool  # True = RECIBIDA, False = DEVUELTA
    errors: list[SriErrorDetail]


@dataclass(frozen=True)
class AutorizacionResult:
    status: str  # "AUTORIZADO" | "RECHAZADO" | "EN_PROCESO"
    authorization_number: str | None = None
    authorized_at: str | None = None
    signed_xml: str | None = None  # eco del XML firmado que el SRI autorizó (AUTORIZADO)
    errors: list[SriErrorDetail] | None = None


class ISriClient(ABC):
    @abstractmethod
    def recepcion(self, *, environment: str, xmls: list[str]) -> RecepcionResult:
        """POST RecepcionComprobantesOffline (validarComprobante)."""

    @abstractmethod
    def autorizacion(self, *, environment: str, access_key: str) -> AutorizacionResult:
        """POST AutorizacionComprobantesOffline (autorizacionComprobante)."""


class IDocumentStorage(ABC):
    @abstractmethod
    def put_authorized_document(
        self,
        *,
        tenant_id: str,
        document_id: str,
        year: int,
        signed_xml: str,
        ride_pdf: bytes,
    ) -> tuple[str, str]:
        """Store the signed XML + RIDE PDF with LegalHold=ON. Returns (xml_s3_key, ride_s3_key)."""


class IQueuePublisher(ABC):
    @abstractmethod
    def enqueue_poll(
        self,
        *,
        tenant_id: str,
        document_id: str,
        access_key: str,
        attempt: int,
        delay_seconds: int,
    ) -> None:
        """Send a POLL message to the invoice-poll queue with a delay."""

    @abstractmethod
    def publish_event(self, event: DomainEvent) -> None:
        """Publish a domain event to the email_notifications queue."""
