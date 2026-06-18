from __future__ import annotations

import secrets
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from lambdas.documents.domain.access_key import generate_access_key
from lambdas.documents.domain.commands import EmitDocumentCommand, LineData
from lambdas.documents.domain.entities import Document, DocumentStatus, InvoiceLine
from lambdas.documents.domain.errors import (
    CertificateNotUploadedError,
    DocumentLimitReachedError,
    InvalidIssuedDateError,
)
from lambdas.documents.domain.iva_rates import iva_rate_for
from lambdas.documents.domain.repositories.i_documents_repository import IDocumentsRepository
from lambdas.documents.domain.repositories.i_sequences_port import ISequencesPort
from shared.errors import ValidationError


def _compute_totals(
    lines_data: list[LineData],
    issued_at: date,
) -> tuple[list[InvoiceLine], Decimal, Decimal, Decimal, Decimal, Decimal, Decimal]:
    if not lines_data:
        raise ValidationError("El documento debe tener al menos una línea de detalle.")

    applicable_rate = iva_rate_for(issued_at)

    lines: list[InvoiceLine] = []
    subtotal = Decimal("0.00")
    total_discount = Decimal("0.00")
    iva_15 = Decimal("0.00")
    iva_5 = Decimal("0.00")

    for raw in lines_data:
        qty = raw.quantity
        unit_price = raw.unit_price
        discount = raw.discount
        iva_rate_str = raw.iva_rate

        line_subtotal = (qty * unit_price - discount).quantize(Decimal("0.01"))

        if iva_rate_str == "15":
            iva_amount = (line_subtotal * applicable_rate / 100).quantize(Decimal("0.01"))
            iva_15 += iva_amount
        elif iva_rate_str == "5":
            iva_amount = (line_subtotal * Decimal("5") / 100).quantize(Decimal("0.01"))
            iva_5 += iva_amount
        else:
            iva_amount = Decimal("0.00")

        lines.append(
            InvoiceLine(
                code=raw.code,
                description=raw.description,
                quantity=qty,
                unit_price=unit_price,
                discount=discount,
                subtotal=line_subtotal,
                iva_rate=iva_rate_str,
                iva_amount=iva_amount,
                total=(line_subtotal + iva_amount).quantize(Decimal("0.01")),
            )
        )
        subtotal += line_subtotal
        total_discount += discount

    total = subtotal + iva_15 + iva_5
    return (
        lines,
        subtotal.quantize(Decimal("0.01")),
        total_discount.quantize(Decimal("0.01")),
        iva_15.quantize(Decimal("0.01")),
        iva_5.quantize(Decimal("0.01")),
        Decimal("0.00"),
        total.quantize(Decimal("0.01")),
    )


def _random_numeric_code() -> str:
    return "".join(str(secrets.randbelow(10)) for _ in range(8))


class EmitDocumentUseCase:
    def __init__(
        self,
        docs_repo: IDocumentsRepository,
        sequences_port: ISequencesPort,
    ) -> None:
        self._docs_repo = docs_repo
        self._sequences_port = sequences_port

    def execute(self, cmd: EmitDocumentCommand) -> Document:
        if not cmd.certificate_secret_arn:
            raise CertificateNotUploadedError()

        today = datetime.now(UTC).date()
        if cmd.issued_at > today:
            raise InvalidIssuedDateError()

        if cmd.monthly_limit != -1:
            count = self._docs_repo.count_this_month(cmd.tenant_id, cmd.sri_environment)
            if count >= cmd.monthly_limit:
                raise DocumentLimitReachedError()

        sequential = self._sequences_port.reserve_next(cmd.tenant_id, cmd.serie)

        numeric_code = _random_numeric_code()
        access_key = generate_access_key(
            issued_at=cmd.issued_at,
            doc_type=cmd.doc_type,
            ruc=cmd.ruc,
            environment=cmd.sri_environment,
            serie=cmd.serie,
            sequential=sequential,
            numeric_code=numeric_code,
        )

        lines, subtotal, total_discount, iva_15, iva_5, iva_0, total = _compute_totals(
            cmd.lines, cmd.issued_at
        )

        return Document(
            document_id=str(uuid4()),
            tenant_id=cmd.tenant_id,
            doc_type=cmd.doc_type,
            status=DocumentStatus.PENDING,
            serie=cmd.serie,
            sequential=sequential,
            access_key=access_key,
            client_id=cmd.client_id,
            buyer_id_type=cmd.buyer_id_type,
            buyer_id=cmd.buyer_id,
            buyer_name=cmd.buyer_name,
            buyer_email=cmd.buyer_email,
            issued_at=cmd.issued_at,
            sri_environment=cmd.sri_environment,
            subtotal=subtotal,
            total_discount=total_discount,
            iva_15=iva_15,
            iva_5=iva_5,
            iva_0=iva_0,
            total=total,
            payment_method=cmd.payment_method,
            lines=lines,
            created_by=cmd.created_by,
        )
