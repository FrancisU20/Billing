from __future__ import annotations

import secrets
from decimal import Decimal
from uuid import uuid4

from lambdas.documents.domain.access_key import generate_access_key
from lambdas.documents.domain.commands import CreditNoteLineData, EmitCreditNoteCommand
from lambdas.documents.domain.entities import Document, DocumentStatus, InvoiceLine
from lambdas.documents.domain.errors import (
    CertificateNotUploadedError,
    CreditedQuantityExceedsOriginalError,
    DocumentLimitReachedError,
    InvalidIssuedDateError,
    ParentDocumentNotAuthorizedError,
)
from lambdas.documents.domain.repositories.i_documents_repository import IDocumentsRepository
from lambdas.documents.domain.repositories.i_sequences_port import ISequencesPort
from lambdas.documents.domain.totals import aggregate_line_totals
from shared.dates import today_ecuador
from shared.errors import ValidationError

_CREDIT_NOTE_DOC_TYPE = "04"
_INVOICE_DOC_TYPE = "01"


def _random_numeric_code() -> str:
    return "".join(str(secrets.randbelow(10)) for _ in range(8))


class EmitCreditNoteUseCase:
    """Emite una Nota de Credito (04) que acredita, total o parcialmente, una factura
    propia ya AUTORIZADA. A diferencia de EmitDocumentUseCase, las lineas no se resuelven
    contra el catalogo de productos vigente — se copian de los snapshots ya persistidos de
    la factura padre, solo permitiendo reducir la cantidad acreditada.
    """

    def __init__(self, docs_repo: IDocumentsRepository, sequences_port: ISequencesPort) -> None:
        self._docs_repo = docs_repo
        self._sequences_port = sequences_port

    def execute(self, cmd: EmitCreditNoteCommand) -> Document:
        if not cmd.certificate_secret_arn:
            raise CertificateNotUploadedError()

        if cmd.issued_at > today_ecuador():
            raise InvalidIssuedDateError()

        if not cmd.credit_note_reason.strip():
            raise ValidationError("Debes indicar el motivo de la nota de crédito.")

        if not cmd.lines:
            raise ValidationError("La nota de crédito debe tener al menos una línea.")

        parent = self._docs_repo.get(cmd.tenant_id, cmd.related_document_id)

        if parent.status != DocumentStatus.AUTHORIZED:
            raise ParentDocumentNotAuthorizedError()

        if parent.doc_type != _INVOICE_DOC_TYPE:
            raise ValidationError(
                "Una nota de crédito solo puede acreditar una factura (01), no otra "
                "nota de crédito."
            )

        if cmd.monthly_limit != -1:
            count = self._docs_repo.count_this_month(cmd.tenant_id, cmd.sri_environment)
            if count >= cmd.monthly_limit:
                raise DocumentLimitReachedError()

        lines = self._build_credit_lines(parent.lines, cmd.lines)
        subtotal, total_discount, iva_15, iva_5, iva_0, total = aggregate_line_totals(lines)

        sequential = self._sequences_port.reserve_next(
            cmd.tenant_id, cmd.serie, doc_type=_CREDIT_NOTE_DOC_TYPE
        )
        numeric_code = _random_numeric_code()
        access_key = generate_access_key(
            issued_at=cmd.issued_at,
            doc_type=_CREDIT_NOTE_DOC_TYPE,
            ruc=cmd.ruc,
            environment=cmd.sri_environment,
            serie=cmd.serie,
            sequential=sequential,
            numeric_code=numeric_code,
        )

        return Document(
            document_id=str(uuid4()),
            tenant_id=cmd.tenant_id,
            doc_type=_CREDIT_NOTE_DOC_TYPE,
            status=DocumentStatus.PENDING,
            serie=cmd.serie,
            sequential=sequential,
            access_key=access_key,
            client_id=parent.client_id,
            buyer_id_type=parent.buyer_id_type,
            buyer_id=parent.buyer_id,
            buyer_name=parent.buyer_name,
            buyer_email=parent.buyer_email,
            issued_at=cmd.issued_at,
            sri_environment=cmd.sri_environment,
            subtotal=subtotal,
            total_discount=total_discount,
            iva_15=iva_15,
            iva_5=iva_5,
            iva_0=iva_0,
            total=total,
            payment_method=parent.payment_method,
            lines=lines,
            created_by=cmd.created_by,
            related_document_id=parent.document_id,
            credit_note_reason=cmd.credit_note_reason.strip(),
        )

    def _build_credit_lines(
        self,
        parent_lines: list[InvoiceLine],
        requested: list[CreditNoteLineData],
    ) -> list[InvoiceLine]:
        lines: list[InvoiceLine] = []
        for item in requested:
            if item.parent_line_index < 0 or item.parent_line_index >= len(parent_lines):
                raise ValidationError(
                    "La nota de crédito referencia una línea que no existe en la factura original."
                )
            parent_line = parent_lines[item.parent_line_index]

            if item.quantity <= 0 or item.quantity > parent_line.quantity:
                raise CreditedQuantityExceedsOriginalError()

            # Escala los montos YA calculados de la linea original (no se re-deriva la
            # tasa de IVA aplicable) — garantiza que la nota de credito refleje
            # exactamente lo facturado originalmente, sin importar si la tabla de tasas
            # de IVA cambio entre la fecha de la factura y la de esta nota de credito.
            ratio = item.quantity / parent_line.quantity
            discount = (parent_line.discount * ratio).quantize(Decimal("0.01"))
            line_subtotal = (parent_line.subtotal * ratio).quantize(Decimal("0.01"))
            iva_amount = (parent_line.iva_amount * ratio).quantize(Decimal("0.01"))

            lines.append(
                InvoiceLine(
                    code=parent_line.code,
                    description=parent_line.description,
                    quantity=item.quantity,
                    unit_price=parent_line.unit_price,
                    discount=discount,
                    subtotal=line_subtotal,
                    iva_rate=parent_line.iva_rate,
                    iva_amount=iva_amount,
                    total=(line_subtotal + iva_amount).quantize(Decimal("0.01")),
                    product_id=parent_line.product_id,
                )
            )
        return lines
