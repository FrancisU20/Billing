from __future__ import annotations

from lambdas.clients.domain.entity import Client
from lambdas.clients.domain.repositories.i_client_repository import IClientRepository


class DeleteClientUseCase:
    def __init__(self, repo: IClientRepository) -> None:
        self._repo = repo

    def execute(self, client_id: str, deleted_by: str) -> Client:
        client = self._repo.get_by_id(client_id)
        client.soft_delete(deleted_by)
        return client
