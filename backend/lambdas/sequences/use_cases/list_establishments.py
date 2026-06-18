from __future__ import annotations

from lambdas.sequences.domain.entities import Establishment
from lambdas.sequences.domain.repositories.i_sequences_repository import ISequencesRepository


class ListEstablishmentsUseCase:
    def __init__(self, repo: ISequencesRepository) -> None:
        self._repo = repo

    def execute(self, tenant_id: str) -> list[Establishment]:
        return self._repo.list_establishments(tenant_id)
