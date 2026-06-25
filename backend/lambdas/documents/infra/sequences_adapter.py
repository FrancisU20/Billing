from __future__ import annotations

from lambdas.documents.domain.repositories.i_sequences_port import ISequencesPort
from lambdas.sequences.infra.sequences_repository import DynamoSequencesRepository


class DynamoSequencesAdapter(ISequencesPort):
    """Adapts DynamoSequencesRepository.reserve_next() to the documents port."""

    def __init__(self, sequences_table) -> None:
        self._repo = DynamoSequencesRepository(sequences_table)

    def reserve_next(self, tenant_id: str, serie: str, doc_type: str = "01") -> int:
        return self._repo.reserve_next(tenant_id, serie, doc_type)
