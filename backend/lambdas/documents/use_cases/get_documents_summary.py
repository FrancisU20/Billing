from __future__ import annotations

from lambdas.documents.domain.entities import DocumentSummary
from lambdas.documents.domain.repositories.i_documents_repository import IDocumentsRepository


class GetDocumentsSummaryUseCase:
    def __init__(self, repo: IDocumentsRepository) -> None:
        self._repo = repo

    def execute(self, tenant_id: str) -> DocumentSummary:
        return self._repo.summary_this_month(tenant_id)
