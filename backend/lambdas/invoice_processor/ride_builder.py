from __future__ import annotations

"""
RIDE (Representación Impresa del Documento Electrónico) — PDF de la factura
autorizada. Cubre los campos obligatorios del RIDE (Ficha Técnica SRI) en texto;
sin logo ni código de barras real en este sprint (ver `INVOICES.md`, fuera de
alcance — evita sumar python-barcode sin necesidad; Pillow ya entra como
dependencia transitiva de reportlab, no por elección propia).
"""

import io
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from lambdas.documents.domain.entities import Document
from lambdas.tenants.domain.tenant import Tenant
from shared.dates import format_date_ecuador, format_datetime_ecuador

_styles = getSampleStyleSheet()
_small = ParagraphStyle("small", parent=_styles["Normal"], fontSize=8, leading=10)

_DOC_TYPE_LABELS = {"01": "FACTURA", "04": "NOTA DE CRÉDITO"}


def _discount_cell(line) -> str:
    """'$5.00 (20.00%)' sobre el precio original, o '—' sin descuento.

    Solo de confianza/transparencia ante el comprador (Sprint 2e) — el % no es
    un campo del XML/XSD del SRI, se deriva de `discount`/`unit_price` ya
    persistidos, no agrega ningún dato nuevo a lo fiscal.
    """
    if line.discount == 0:
        return "—"
    gross = line.quantity * line.unit_price
    if gross <= 0:
        return f"${line.discount:.2f}"
    pct = (line.discount / gross * 100).quantize(Decimal("0.01"))
    return f"${line.discount:.2f} ({pct}%)"


def build_ride_pdf(document: Document, tenant: Tenant, parent: Document | None = None) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
    )
    elements: list = []

    elements.append(Paragraph(tenant.legal_name, _styles["Heading2"]))
    if tenant.trade_name:
        elements.append(Paragraph(tenant.trade_name, _styles["Normal"]))
    elements.append(Paragraph(f"RUC: {tenant.ruc}", _styles["Normal"]))
    elements.append(Paragraph(f"Dirección matriz: {tenant.address}", _styles["Normal"]))
    elements.append(
        Paragraph(
            f"Ambiente: {'PRUEBAS' if document.sri_environment == 'testing' else 'PRODUCCIÓN'}",
            _styles["Normal"],
        )
    )
    elements.append(Spacer(1, 0.5 * cm))

    doc_label = _DOC_TYPE_LABELS.get(document.doc_type, "DOCUMENTO")
    elements.append(
        Paragraph(f"{doc_label} No. {document.sequential_display}", _styles["Heading3"])
    )
    elements.append(
        Paragraph(f"Fecha de emisión: {format_date_ecuador(document.issued_at)}", _styles["Normal"])
    )
    elements.append(Paragraph(f"Clave de acceso: {document.access_key}", _small))
    if parent is not None:
        elements.append(Paragraph(f"Modifica a: Factura {parent.sequential_display}", _small))
        if document.credit_note_reason:
            elements.append(Paragraph(f"Motivo: {document.credit_note_reason}", _small))
    if document.authorization_number:
        elements.append(
            Paragraph(f"Número de autorización: {document.authorization_number}", _small)
        )
    if document.authorized_at:
        elements.append(
            Paragraph(
                f"Fecha de autorización: {format_datetime_ecuador(document.authorized_at)}",
                _small,
            )
        )
    elements.append(Spacer(1, 0.5 * cm))

    elements.append(Paragraph("Datos del comprador", _styles["Heading4"]))
    elements.append(Paragraph(f"Razón social: {document.buyer_name}", _styles["Normal"]))
    elements.append(
        Paragraph(
            f"Identificación ({document.buyer_id_type}): {document.buyer_id}", _styles["Normal"]
        )
    )
    elements.append(Spacer(1, 0.5 * cm))

    detail_rows = [
        ["Cód.", "Descripción", "Cant.", "P. Unit. orig.", "Desc.", "Subtotal", "IVA", "Total"]
    ]
    for line in document.lines:
        detail_rows.append(
            [
                line.code,
                line.description,
                str(line.quantity),
                str(line.unit_price),
                _discount_cell(line),
                str(line.subtotal),
                f"{line.iva_rate}%" if line.iva_rate != "EXENTO" else "EXENTO",
                str(line.total),
            ]
        )
    detail_table = Table(
        detail_rows,
        repeatRows=1,
        hAlign="LEFT",
        colWidths=[1.6 * cm, 5.0 * cm, 1.2 * cm, 2.1 * cm, 2.4 * cm, 2.1 * cm, 1.4 * cm, 2.1 * cm],
    )
    detail_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    elements.append(detail_table)
    elements.append(Spacer(1, 0.5 * cm))

    totals_rows = [
        ["Subtotal", str(document.subtotal)],
        ["Descuento", str(document.total_discount)],
        ["IVA 15%", str(document.iva_15)],
        ["IVA 5%", str(document.iva_5)],
        ["VALOR TOTAL", str(document.total)],
    ]
    totals_table = Table(totals_rows, colWidths=[8 * cm, 4 * cm], hAlign="RIGHT")
    totals_table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("LINEABOVE", (0, -1), (-1, -1), 0.5, colors.black),
            ]
        )
    )
    elements.append(totals_table)

    doc.build(elements)
    return buffer.getvalue()
