from __future__ import annotations

from lambdas.clients.domain.commands import UpdateClientCommand
from lambdas.clients.domain.entity import Client
from lambdas.clients.domain.repositories.i_client_repository import IClientRepository


class UpdateClientUseCase:
    def __init__(self, repo: IClientRepository) -> None:
        self._repo = repo

    def execute(self, cmd: UpdateClientCommand) -> Client:
        client = self._repo.get_by_id(cmd.client_id)
        client.update(cmd)
        return client
