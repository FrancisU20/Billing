from __future__ import annotations

from abc import ABC, abstractmethod

from lambdas._base.idempotency import IdempotencyContext
from lambdas.sequences.domain.entities import EmissionPoint, Establishment


class ISequencesRepository(ABC):
    @abstractmethod
    def get_establishment(self, tenant_id: str, code: str) -> Establishment:
        """Return the establishment or raise EstablishmentNotFoundError."""

    @abstractmethod
    def find_establishment(self, tenant_id: str, code: str) -> Establishment | None:
        """Return the establishment or None if it does not exist."""

    @abstractmethod
    def list_establishments(self, tenant_id: str) -> list[Establishment]:
        """Return all establishments for the tenant, ordered by code."""

    @abstractmethod
    def commit(
        self,
        *,
        establishment: Establishment,
        action: str,
        user_id: str,
        new_emission_point: EmissionPoint | None = None,
        update_sequence: tuple[str, int] | None = None,
        idempotency: IdempotencyContext | None = None,
        response: dict | None = None,
    ) -> None:
        """Persist the establishment.

        new_emission_point: if set, atomically creates the SEQ counter item alongside
                            the establishment update.
        update_sequence: (serie, new_initial) — resets the SEQ counter for an existing
                         emission point whose initial_sequential changed.
        """

    @abstractmethod
    def has_sequence_started(self, tenant_id: str, serie: str) -> bool:
        """Return True if at least one document has been issued for this serie (estab+punto)."""

    @abstractmethod
    def reserve_next(self, tenant_id: str, serie: str, doc_type: str = "01") -> int:
        """Atomically increment and return the next sequential number.

        Contador independiente por doc_type (exigencia del SRI: secuencial separado por
        tipo de comprobante). Raises SequenceExhaustedError if the counter has reached
        999,999,999. Not exposed via HTTP — called only by the documents Lambda.
        """

    @abstractmethod
    def bootstrap_testing_point(self, tenant_id: str) -> None:
        """Idempotently create establishment 001 with emission point 099 (testing).

        Called by the certificates Lambda after a successful certificate upload.
        Silently no-ops if the establishment or the 099 point already exist.
        """
