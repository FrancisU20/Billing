from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from lambdas._base.idempotency import IdempotencyContext
from lambdas.documents.domain.entities import (
    BuyerNotificationStatus,
    Document,
    DocumentStatus,
    DocumentSummary,
)


class IDocumentsRepository(ABC):
    @abstractmethod
    def get(self, tenant_id: str, document_id: str) -> Document:
        """Return the document or raise DocumentNotFoundError."""

    @abstractmethod
    def list(
        self,
        tenant_id: str,
        *,
        status: str | None = None,
        doc_type: str | None = None,
        serie: str | None = None,
        q: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 20,
        cursor: str | None = None,
    ) -> tuple[list[Document], str | None]:
        """Return (documents sorted newest-first, next_cursor)."""

    @abstractmethod
    def count_this_month(self, tenant_id: str, sri_environment: str) -> int:
        """Count non-deleted documents emitted this calendar month."""

    @abstractmethod
    def summary_this_month(self, tenant_id: str) -> DocumentSummary:
        """Return operational summary for the current Ecuador calendar month."""

    @abstractmethod
    def count(
        self,
        tenant_id: str,
        *,
        status: str | None = None,
        doc_type: str | None = None,
        serie: str | None = None,
        q: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> int:
        """Count documents matching the same filters as `list()`."""

    @abstractmethod
    def save(
        self,
        document: Document,
        *,
        idempotency: IdempotencyContext | None = None,
        response: dict | None = None,
        override_reason: str | None = None,
        user_id: str | None = None,
    ) -> None:
        """Persist a new document atomically with the idempotency completion.

        When `override_reason` is set (the discount ceiling was overridden), an
        audit record is written transactionally alongside the document.
        """

    @abstractmethod
    def update_status(
        self,
        tenant_id: str,
        document_id: str,
        *,
        expected_status: DocumentStatus,
        new_status: DocumentStatus,
        increment_retry: bool = False,
        authorization_number: str | None = None,
        authorized_at: datetime | None = None,
        rejected_at: datetime | None = None,
        xml_s3_key: str | None = None,
        ride_s3_key: str | None = None,
        sri_errors: list[dict] | None = None,
    ) -> bool:
        """Conditional status transition used by invoice_processor.

        Only applies if the document's current status equals `expected_status`.
        Returns False (no-op, no exception) when it doesn't — this happens when
        SQS redelivers a SIGN/POLL message that was already processed, and the
        caller must treat it as a successful no-op, not a failure.
        """

    @abstractmethod
    def annul(
        self,
        tenant_id: str,
        document_id: str,
        *,
        reason: str,
        user_id: str,
        access_key: str,
        idempotency: IdempotencyContext | None = None,
        response: dict | None = None,
    ) -> None:
        """Transition AUTHORIZED -> ANNULLED atomically with an audit record.

        Raises DocumentNotAuthorizedError if the document's current status isn't
        AUTHORIZED (lost a race, or was already annulled).
        """

    @abstractmethod
    def retry(
        self,
        tenant_id: str,
        document_id: str,
        *,
        user_id: str,
        access_key: str,
        idempotency: IdempotencyContext | None = None,
        response: dict | None = None,
    ) -> None:
        """Transition REJECTED -> PENDING atomically with an audit record, incrementing
        manual_retry_count. Reuses the existing access_key/sequential — no new ones are
        generated.

        Raises DocumentRetryNotEligibleError if the document's current status isn't
        REJECTED (lost a race, or already retried by another request).
        """

    @abstractmethod
    def mark_annulled_by_credit_note(
        self,
        tenant_id: str,
        document_id: str,
        *,
        credit_note_id: str,
    ) -> None:
        """Link a Factura (doc_type='01') to the Nota de Credito that annuls it 100%.

        `status` never changes — the invoice stays AUTHORIZED forever (that is what the
        SRI actually recognizes). Called right when the credit note is CREATED (not when
        it's authorized), so `EmitCreditNoteUseCase` can immediately block a second
        full-annulment credit note against the same invoice. The UI derives a banner by
        looking up the referenced credit note's live status.
        """

    @abstractmethod
    def mark_buyer_notification_status(
        self,
        tenant_id: str,
        document_id: str,
        *,
        status: BuyerNotificationStatus,
        notified_at: datetime | None = None,
        error: str | None = None,
    ) -> bool:
        """Mark buyer email delivery state.

        Returns False when the document already has a terminal buyer notification status.
        This makes repeated SQS deliveries idempotent and prevents duplicated buyer emails.
        """

    @abstractmethod
    def begin_buyer_notification(self, tenant_id: str, document_id: str) -> bool:
        """Acquire the buyer notification send lock.

        Returns False if another worker already sent, skipped, or is currently sending it.
        A previous FAILED state is retryable.
        """
