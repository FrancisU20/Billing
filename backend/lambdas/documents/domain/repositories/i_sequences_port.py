from __future__ import annotations

from abc import ABC, abstractmethod


class ISequencesPort(ABC):
    @abstractmethod
    def reserve_next(self, tenant_id: str, serie: str) -> int:
        """Atomically increment and return the next sequential number for serie.

        Raises SequenceExhaustedError if the counter has reached 999,999,999.
        """
