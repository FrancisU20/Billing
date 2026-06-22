from __future__ import annotations

from dataclasses import replace
from datetime import date

from lambdas.documents.domain.commands import AnnulDocumentCommand
from lambdas.documents.domain.entities import Document, DocumentStatus
from lambdas.documents.domain.errors import (
    AnnulmentWindowExpiredError,
    ConsumerFinalCannotBeAnnulledError,
    DocumentNotAuthorizedError,
)
from lambdas.documents.domain.repositories.i_documents_repository import IDocumentsRepository
from shared.dates import now_utc, today_ecuador

# SRI Res. NAC-DGERCGC25-00000014/00000017: anulacion "en linea" solo hasta el dia 7 del
# mes siguiente a la emision. No se ajusta al siguiente dia habil si cae feriado/fin de
# semana (calendario de feriados de Ecuador fuera de alcance) — deliberadamente mas
# restrictivo que el SRI en esos casos puntuales, nunca mas permisivo.
_ANNULMENT_DEADLINE_DAY = 7
# Buyer ID type "07" = Consumidor Final (catalogo SRI) — no anulable desde enero 2026.
_CONSUMIDOR_FINAL_ID_TYPE = "07"


def _annulment_deadline(issued_at: date) -> date:
    if issued_at.month == 12:
        return date(issued_at.year + 1, 1, _ANNULMENT_DEADLINE_DAY)
    return date(issued_at.year, issued_at.month + 1, _ANNULMENT_DEADLINE_DAY)


class AnnulDocumentUseCase:
    def __init__(self, repo: IDocumentsRepository) -> None:
        self._repo = repo

    def execute(self, command: AnnulDocumentCommand) -> Document:
        document = self._repo.get(command.tenant_id, command.document_id)

        if document.status != DocumentStatus.AUTHORIZED:
            raise DocumentNotAuthorizedError()
        if document.buyer_id_type == _CONSUMIDOR_FINAL_ID_TYPE:
            raise ConsumerFinalCannotBeAnnulledError()
        if today_ecuador() > _annulment_deadline(document.issued_at):
            raise AnnulmentWindowExpiredError()

        return replace(
            document,
            status=DocumentStatus.ANNULLED,
            annulled_at=now_utc(),
            annulled_by=command.user_id,
            annulment_reason=command.reason,
        )
