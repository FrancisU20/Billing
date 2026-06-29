from __future__ import annotations

from decimal import Decimal

from lambdas.documents.domain.entities import InvoiceLine

_MONEY = Decimal("0.01")


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(_MONEY)


def line_gross_amount(quantity: Decimal, unit_price: Decimal) -> Decimal:
    return quantize_money(quantity * unit_price)


def line_subtotal_amount(quantity: Decimal, unit_price: Decimal, discount: Decimal) -> Decimal:
    return quantize_money(quantity * unit_price - discount)


def iva_amount_for_rate(
    *,
    subtotal: Decimal,
    iva_rate: str,
    applicable_15_rate: Decimal,
) -> Decimal:
    if iva_rate == "15":
        return quantize_money(subtotal * applicable_15_rate / 100)
    if iva_rate == "5":
        return quantize_money(subtotal * Decimal("5") / 100)
    return Decimal("0.00")


def line_total_amount(subtotal: Decimal, iva_amount: Decimal) -> Decimal:
    return quantize_money(subtotal + iva_amount)


def scale_credit_line_amounts(
    *,
    parent_line: InvoiceLine,
    credited_quantity: Decimal,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """Scale already-persisted invoice amounts for a credit note line.

    This deliberately does not re-derive tax rates from dates. Credit notes must mirror
    the original authorized invoice amounts, even if the IVA table changes later.

    Returns (discount, subtotal, iva_amount, total).
    """
    ratio = credited_quantity / parent_line.quantity
    discount = quantize_money(parent_line.discount * ratio)
    subtotal = quantize_money(parent_line.subtotal * ratio)
    iva_amount = quantize_money(parent_line.iva_amount * ratio)
    return discount, subtotal, iva_amount, line_total_amount(subtotal, iva_amount)


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
    iva_0 = Decimal("0.00")

    for line in lines:
        subtotal += line.subtotal
        total_discount += line.discount
        if line.iva_rate == "15":
            iva_15 += line.iva_amount
        elif line.iva_rate == "5":
            iva_5 += line.iva_amount
        elif line.iva_rate in {"0", "EXENTO"}:
            iva_0 += line.iva_amount

    total = subtotal + iva_15 + iva_5 + iva_0
    return (
        quantize_money(subtotal),
        quantize_money(total_discount),
        quantize_money(iva_15),
        quantize_money(iva_5),
        quantize_money(iva_0),
        quantize_money(total),
    )
