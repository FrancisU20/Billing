from __future__ import annotations

"""
RIDE (Representación Impresa del Documento Electrónico) — PDF de la factura
autorizada. Cubre los campos obligatorios del RIDE (Ficha Técnica SRI) en texto;
sin logo ni código de barras real en este sprint (ver `INVOICES.md`, fuera de
alcance — evita sumar python-barcode sin necesidad; Pillow ya entra como
dependencia transitiva de reportlab, no por elección propia).
"""

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from lambdas.documents.domain.entities import Document
from lambdas.tenants.domain.tenant import Tenant

_styles = getSampleStyleSheet()
_small = ParagraphStyle("small", parent=_styles["Normal"], fontSize=8, leading=10)


def build_ride_pdf(document: Document, tenant: Tenant) -> bytes:
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

    elements.append(Paragraph(f"FACTURA No. {document.sequential_display}", _styles["Heading3"]))
    elements.append(
        Paragraph(f"Fecha de emisión: {document.issued_at.isoformat()}", _styles["Normal"])
    )
    elements.append(Paragraph(f"Clave de acceso: {document.access_key}", _small))
    if document.authorization_number:
        elements.append(
            Paragraph(f"Número de autorización: {document.authorization_number}", _small)
        )
    if document.authorized_at:
        elements.append(
            Paragraph(f"Fecha de autorización: {document.authorized_at.isoformat()}", _small)
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

    detail_rows = [["Cód.", "Descripción", "Cant.", "P. Unit.", "Desc.", "IVA", "Total"]]
    for line in document.lines:
        detail_rows.append(
            [
                line.code,
                line.description,
                str(line.quantity),
                str(line.unit_price),
                str(line.discount),
                f"{line.iva_rate}%" if line.iva_rate != "EXENTO" else "EXENTO",
                str(line.total),
            ]
        )
    detail_table = Table(detail_rows, repeatRows=1, hAlign="LEFT")
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
