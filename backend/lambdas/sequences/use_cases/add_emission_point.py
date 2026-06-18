from __future__ import annotations

from dataclasses import dataclass

from lambdas.sequences.domain.commands import AddEmissionPointCommand
from lambdas.sequences.domain.entities import EmissionPoint, Establishment
from lambdas.sequences.domain.errors import (
    EmissionPointCode099ReservedError,
    EmissionPointCodeExistsError,
)
from lambdas.sequences.domain.repositories.i_sequences_repository import ISequencesRepository


@dataclass
class AddEmissionPointResult:
    establishment: Establishment
    new_emission_point: EmissionPoint


class AddEmissionPointUseCase:
    def __init__(self, repo: ISequencesRepository) -> None:
        self._repo = repo

    def execute(self, cmd: AddEmissionPointCommand) -> AddEmissionPointResult:
        if cmd.code == "099":
            raise EmissionPointCode099ReservedError()

        establishment = self._repo.get_establishment(cmd.tenant_id, cmd.establishment_code)

        if establishment.has_emission_point(cmd.code):
            raise EmissionPointCodeExistsError()

        ep = EmissionPoint(
            code=cmd.code,
            label=cmd.label.strip(),
            initial_sequential=cmd.initial_sequential,
        )
        establishment.add_emission_point(ep, cmd.created_by)

        return AddEmissionPointResult(establishment=establishment, new_emission_point=ep)
