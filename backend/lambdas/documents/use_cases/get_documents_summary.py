from __future__ import annotations

from dataclasses import replace

from lambdas.documents.domain.entities import DocumentSummary
from lambdas.documents.domain.repositories.i_documents_repository import IDocumentsRepository


class GetDocumentsSummaryUseCase:
    def __init__(self, repo: IDocumentsRepository) -> None:
        self._repo = repo

    def execute(self, tenant_id: str, monthly_limit: int | None = None) -> DocumentSummary:
        summary = self._repo.summary_this_month(tenant_id)
        if monthly_limit is None:
            return summary
        return replace(summary, document_limit=monthly_limit, is_unlimited=monthly_limit == -1)
