from __future__ import annotations

from lambdas.sequences.domain.commands import CreateEstablishmentCommand
from lambdas.sequences.domain.entities import Establishment
from lambdas.sequences.domain.errors import EstablishmentCodeExistsError
from lambdas.sequences.domain.repositories.i_sequences_repository import ISequencesRepository


class CreateEstablishmentUseCase:
    def __init__(self, repo: ISequencesRepository) -> None:
        self._repo = repo

    def execute(self, cmd: CreateEstablishmentCommand) -> Establishment:
        existing = self._repo.find_establishment(cmd.tenant_id, cmd.code)
        if existing is not None:
            raise EstablishmentCodeExistsError()

        return Establishment(
            code=cmd.code,
            label=cmd.label.strip(),
            tenant_id=cmd.tenant_id,
            created_by=cmd.created_by,
            updated_by=cmd.created_by,
        )
