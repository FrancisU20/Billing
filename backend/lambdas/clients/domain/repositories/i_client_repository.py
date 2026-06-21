from __future__ import annotations

from abc import ABC, abstractmethod

from lambdas._base.idempotency import IdempotencyContext
from lambdas.clients.domain.entity import Client


class IClientRepository(ABC):
    @abstractmethod
    def get_by_id(self, client_id: str) -> Client:
        """Raises ClientNotFoundError if not found or soft-deleted."""

    @abstractmethod
    def get_by_identification(
        self, identification: str, exclude_id: str | None = None
    ) -> Client | None:
        """Returns a non-deleted client inside the current tenant."""

    @abstractmethod
    def list(
        self,
        limit: int,
        next_token: str | None,
        status: str | None = None,
        q: str | None = None,
        identification: str | None = None,
        identification_type: str | None = None,
        created_from: str | None = None,
        created_to: str | None = None,
    ) -> tuple[list[Client], str | None]:
        """Returns (items, next_token)."""

    @abstractmethod
    def count(
        self,
        status: str | None = None,
        identification: str | None = None,
        identification_type: str | None = None,
        created_from: str | None = None,
        created_to: str | None = None,
    ) -> int:
        """Count matching `list()` filters, excluding `q` (matched in Python). `identification`
        is a GSI prefix Query (Select=COUNT), so it stays accurate here."""

    @abstractmethod
    def save(self, client: Client, user_id: str) -> None: ...

    @abstractmethod
    def commit(
        self,
        *,
        client: Client,
        user_id: str,
        action: str,
        idempotency: IdempotencyContext | None,
        response: dict | None,
    ) -> None: ...
