from __future__ import annotations

from dataclasses import dataclass

from lambdas.clients.domain.entity import Client
from lambdas.clients.domain.repositories.i_client_repository import IClientRepository


@dataclass(frozen=True)
class ListClientsQuery:
    limit: int
    next_token: str | None = None
    status: str | None = None
    q: str | None = None
    identification: str | None = None
    identification_type: str | None = None
    created_from: str | None = None
    created_to: str | None = None


class ListClientsUseCase:
    def __init__(self, repo: IClientRepository) -> None:
        self._repo = repo

    def execute(self, query: ListClientsQuery) -> tuple[list[Client], str | None]:
        return self._repo.list(
            limit=query.limit,
            next_token=query.next_token,
            status=query.status,
            q=query.q,
            identification=query.identification,
            identification_type=query.identification_type,
            created_from=query.created_from,
            created_to=query.created_to,
        )
