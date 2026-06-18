from __future__ import annotations

from lambdas.documents.domain.commands import GetDocumentCommand
from lambdas.documents.domain.entities import Document
from lambdas.documents.domain.repositories.i_documents_repository import IDocumentsRepository


class GetDocumentUseCase:
    def __init__(self, repo: IDocumentsRepository) -> None:
        self._repo = repo

    def execute(self, cmd: GetDocumentCommand) -> Document:
        return self._repo.get(cmd.tenant_id, cmd.document_id)
