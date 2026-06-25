from __future__ import annotations

from abc import ABC, abstractmethod


class ISequencesPort(ABC):
    @abstractmethod
    def reserve_next(self, tenant_id: str, serie: str, doc_type: str = "01") -> int:
        """Atomically increment and return the next sequential number for serie.

        Cada doc_type tiene su propio contador independiente por serie (exigencia del
        SRI: secuencial separado por tipo de comprobante). Raises SequenceExhaustedError
        if the counter has reached 999,999,999.
        """
