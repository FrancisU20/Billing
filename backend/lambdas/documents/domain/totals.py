from __future__ import annotations

from decimal import Decimal

from lambdas.documents.domain.entities import InvoiceLine


def aggregate_line_totals(
    lines: list[InvoiceLine],
) -> tuple[Decimal, Decimal, Decimal, Decimal, Decimal, Decimal]:
    """Sum already-built InvoiceLines into document-level totals.

    Pure aggregation only — assumes each line's subtotal/iva_amount were already computed
    (catalog lookups, discount-ceiling validation, etc. happen before this). Shared by
    EmitDocumentUseCase and EmitCreditNoteUseCase so the IVA-bucket summation isn't
    duplicated between them.

    Returns (subtotal, total_discount, iva_15, iva_5, iva_0, total).
    """
    subtotal = Decimal("0.00")
    total_discount = Decimal("0.00")
    iva_15 = Decimal("0.00")
    iva_5 = Decimal("0.00")

    for line in lines:
        subtotal += line.subtotal
        total_discount += line.discount
        if line.iva_rate == "15":
            iva_15 += line.iva_amount
        elif line.iva_rate == "5":
            iva_5 += line.iva_amount

    total = subtotal + iva_15 + iva_5
    return (
        subtotal.quantize(Decimal("0.01")),
        total_discount.quantize(Decimal("0.01")),
        iva_15.quantize(Decimal("0.01")),
        iva_5.quantize(Decimal("0.01")),
        Decimal("0.00"),
        total.quantize(Decimal("0.01")),
    )
