from __future__ import annotations

from lambdas.documents.domain.commands import ListDocumentsCommand
from lambdas.documents.domain.entities import Document
from lambdas.documents.domain.repositories.i_documents_repository import IDocumentsRepository


class ListDocumentsUseCase:
    def __init__(self, repo: IDocumentsRepository) -> None:
        self._repo = repo

    def execute(self, cmd: ListDocumentsCommand) -> tuple[list[Document], str | None]:
        return self._repo.list(
            cmd.tenant_id,
            status=cmd.status,
            serie=cmd.serie,
            date_from=cmd.date_from,
            date_to=cmd.date_to,
            limit=cmd.limit,
            cursor=cmd.cursor,
        )
