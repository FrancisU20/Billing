from __future__ import annotations

from abc import ABC, abstractmethod

from lambdas._base.idempotency import IdempotencyContext
from lambdas.documents.domain.entities import Document


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
        serie: str | None = None,
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
    def save(
        self,
        document: Document,
        *,
        idempotency: IdempotencyContext | None = None,
        response: dict | None = None,
    ) -> None:
        """Persist a new document atomically with the idempotency completion."""
