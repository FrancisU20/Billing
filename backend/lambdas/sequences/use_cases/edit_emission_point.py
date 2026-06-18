from __future__ import annotations

from dataclasses import dataclass

from lambdas.sequences.domain.commands import EditEmissionPointCommand
from lambdas.sequences.domain.entities import Establishment
from lambdas.sequences.domain.errors import (
    EmissionPointNotFoundError,
    SequenceAlreadyUsedError,
)
from lambdas.sequences.domain.repositories.i_sequences_repository import ISequencesRepository


@dataclass
class EditEmissionPointResult:
    establishment: Establishment
    update_sequence: tuple[str, int] | None


class EditEmissionPointUseCase:
    def __init__(self, repo: ISequencesRepository) -> None:
        self._repo = repo

    def execute(self, cmd: EditEmissionPointCommand) -> EditEmissionPointResult:
        establishment = self._repo.get_establishment(cmd.tenant_id, cmd.establishment_code)

        ep = establishment.find_emission_point(cmd.code)
        if ep is None:
            raise EmissionPointNotFoundError()

        update_sequence: tuple[str, int] | None = None
        if cmd.initial_sequential is not None and cmd.initial_sequential != ep.initial_sequential:
            serie = cmd.establishment_code + cmd.code
            if self._repo.has_sequence_started(cmd.tenant_id, serie):
                raise SequenceAlreadyUsedError()
            update_sequence = (serie, cmd.initial_sequential)

        establishment.edit_emission_point(
            code=cmd.code,
            label=cmd.label,
            initial_sequential=cmd.initial_sequential,
            updated_by=cmd.updated_by,
        )

        return EditEmissionPointResult(
            establishment=establishment,
            update_sequence=update_sequence,
        )
