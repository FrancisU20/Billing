from __future__ import annotations

from dataclasses import replace

from lambdas.documents.domain.commands import RetryDocumentCommand
from lambdas.documents.domain.entities import Document, DocumentStatus
from lambdas.documents.domain.errors import DocumentRetryNotEligibleError
from lambdas.documents.domain.repositories.i_documents_repository import IDocumentsRepository
from shared.dates import now_utc


class RetryDocumentUseCase:
    """Reintenta un documento (Factura o Nota de Credito) rechazado por el SRI,
    reusando la MISMA clave de acceso/secuencial — la Ficha Tecnica del SRI (seccion 10,
    nota 1) exige reenviar el comprobante corregido sin generar numeros nuevos. Resetea a
    PENDING para que vuelva a pasar por SIGN (rebuild XML + resign + recepcion), no por
    POLL: la mayoria de rechazos ocurren en recepcion, la clave de acceso nunca quedo
    "recibida" por el SRI.

    Alcance deliberado: solo `status == REJECTED`. FAILED_PERMANENT (polling agotado sin
    respuesta definitiva) necesita una estrategia distinta — reconsultar autorizacion con
    la misma clave de acceso, no reenviar recepcion (reenviar arriesga error 43 "clave
    acceso registrada" porque ahi la recepcion si fue exitosa). Queda fuera de este caso
    de uso a proposito.
    """

    def __init__(self, repo: IDocumentsRepository) -> None:
        self._repo = repo

    def execute(self, command: RetryDocumentCommand) -> Document:
        document = self._repo.get(command.tenant_id, command.document_id)

        if document.status != DocumentStatus.REJECTED:
            raise DocumentRetryNotEligibleError()

        return replace(
            document,
            status=DocumentStatus.PENDING,
            manual_retry_count=document.manual_retry_count + 1,
            retried_at=now_utc(),
        )
