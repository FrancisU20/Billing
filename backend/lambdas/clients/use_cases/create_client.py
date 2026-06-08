from __future__ import annotations

from lambdas.clients.domain.commands import CreateClientCommand
from lambdas.clients.domain.entity import Client
from lambdas.clients.domain.repositories.i_client_repository import IClientRepository


class CreateClientUseCase:
    def __init__(self, repo: IClientRepository) -> None:
        self._repo = repo

    def execute(self, cmd: CreateClientCommand) -> Client:
        return Client.create(cmd)
