"""
Generador de RIDE (Representación Impresa del Documento Electrónico) en PDF.
Usa reportlab para generar el comprobante en formato imprimible.
"""
from io import BytesIO

from app.domain.enums.ambiente_sri import AmbienteSri
from app.infrastructure.sri.iva_config import tarifa_para_codigo
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def generar_ride_factura(datos_comprobante: dict, datos_tenant: dict) -> bytes:
    """
    Genera el PDF/RIDE de una factura autorizada.

    Args:
        datos_comprobante: dict con todos los datos del comprobante (de la DB)
        datos_tenant: dict con razon_social, ruc, logo_url, etc.

    Returns:
        bytes del PDF
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
    )

    styles = getSampleStyleSheet()
    base = styles["Normal"]
    estilo_titulo = ParagraphStyle("titulo", parent=base, fontSize=14, fontName="Helvetica-Bold", alignment=TA_CENTER)
    estilo_normal = ParagraphStyle("normal", parent=base, fontSize=8, fontName="Helvetica")
    estilo_bold = ParagraphStyle("bold", parent=base, fontSize=8, fontName="Helvetica-Bold")
    estilo_center = ParagraphStyle("center", parent=base, fontSize=8, fontName="Helvetica", alignment=TA_CENTER)

    elements = []

    # ── Cabecera ─────────────────────────────────────────────────────────
    razon_social = datos_tenant.get("razon_social", "")
    ruc = datos_tenant.get("ruc", "")
    nombre_comercial = datos_tenant.get("nombre_comercial") or razon_social
    clave_acceso = datos_comprobante.get("clave_acceso", "")
    numero_autorizacion = datos_comprobante.get("numero_autorizacion", "")
    fecha_autorizacion = datos_comprobante.get("fecha_autorizacion", "")
    estab = datos_comprobante.get("establecimiento", "001")
    pto_emi = datos_comprobante.get("punto_emision", "001")
    secuencial = datos_comprobante.get("secuencial", "000000001")
    numero_factura = f"{estab.zfill(3)}-{pto_emi.zfill(3)}-{str(secuencial).zfill(9)}"
    ambiente = "AMBIENTE DE PRUEBAS" if datos_comprobante.get("ambiente") == "1" else "AMBIENTE DE PRODUCCION"

    header_data = [
        [
            Paragraph(nombre_comercial, estilo_titulo),
            "",
            Table([
                [Paragraph("FACTURA", estilo_titulo)],
                [Paragraph(f"No. {numero_factura}", estilo_bold)],
                [Paragraph("NÚMERO DE AUTORIZACIÓN:", estilo_bold)],
                [Paragraph(numero_autorizacion or "—", estilo_normal)],
                [Paragraph(f"FECHA AUTORIZACIÓN: {fecha_autorizacion or '—'}", estilo_normal)],
                [Paragraph(ambiente, ParagraphStyle(
                    "amb", parent=base, fontSize=7, fontName="Helvetica-Bold",
                    alignment=TA_CENTER,
                    textColor=colors.red if AmbienteSri.PRUEBAS in ambiente else colors.green,
                ))],
            ], colWidths=[70 * mm])
        ]
    ]
    header_table = Table(header_data, colWidths=[70 * mm, 15 * mm, 75 * mm])
    header_table.setStyle(TableStyle([
        ("BOX", (2, 0), (2, 0), 0.5, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 3 * mm))

    # Datos del emisor
    emisor_data = [
        ["RUC:", ruc, "DIR MATRIZ:", datos_tenant.get("direccion_matriz", "")],
    ]
    emisor_table = Table(emisor_data, colWidths=[20 * mm, 60 * mm, 25 * mm, 55 * mm])
    emisor_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(emisor_table)
    elements.append(Spacer(1, 3 * mm))

    # ── Datos del comprador ───────────────────────────────────────────────
    datos = datos_comprobante.get("datos", {})
    comprador_data = [
        ["RAZÓN SOCIAL / NOMBRES Y APELLIDOS:", datos.get("razon_social_comprador", ""),
         "FECHA EMISIÓN:", datos.get("fecha_emision", "")],
        ["IDENTIFICACIÓN:", datos.get("identificacion_comprador", ""), "GUÍA DE REMISIÓN:", ""],
    ]
    comprador_table = Table(comprador_data, colWidths=[55 * mm, 65 * mm, 25 * mm, 15 * mm])
    comprador_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(comprador_table)
    elements.append(Spacer(1, 3 * mm))

    # ── Detalles ──────────────────────────────────────────────────────────
    detail_headers = [["Cód.", "Cant.", "Descripción", "P. Unitario", "Dcto.", "P. Total"]]
    detail_rows = []
    for det in datos.get("detalles", []):
        detail_rows.append([
            det.get("codigo_principal", ""),
            f"{float(det.get('cantidad', 0)):.2f}",
            det.get("descripcion", ""),
            f"{float(det.get('precio_unitario', 0)):.4f}",
            f"{float(det.get('descuento', 0)):.2f}",
            f"{float(det.get('precio_total_sin_impuesto', 0)):.2f}",
        ])

    detail_table = Table(
        detail_headers + detail_rows,
        colWidths=[20 * mm, 15 * mm, 70 * mm, 22 * mm, 18 * mm, 18 * mm],
    )
    detail_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(detail_table)
    elements.append(Spacer(1, 3 * mm))

    # ── Totales — la tarifa se infiere de los impuestos del detalle ──────
    total_sin_imp = float(datos.get("total_sin_impuestos", 0))
    total_dcto = float(datos.get("total_descuento", 0))
    importe_total = float(datos.get("importe_total", 0))
    iva_valor = importe_total - total_sin_imp

    # Obtener la tarifa IVA desde los datos del comprobante (no hardcodeada)
    cod_iva = "4"
    for det in datos.get("detalles", []):
        for imp in det.get("impuestos", []):
            if imp.get("codigo") == "2":
                cod_iva = imp.get("codigo_porcentaje", "4")
                break
    tarifa_label = f"{tarifa_para_codigo(cod_iva):.0f}%"

    totales_data = [
        [f"SUBTOTAL {tarifa_label}:", f"${total_sin_imp:.2f}"],
        ["SUBTOTAL 0%:", "$0.00"],
        ["DESCUENTO:", f"${total_dcto:.2f}"],
        [f"IVA {tarifa_label}:", f"${iva_valor:.2f}"],
        ["TOTAL:", f"${importe_total:.2f}"],
    ]
    totales_table = Table(totales_data, colWidths=[40 * mm, 25 * mm], hAlign="RIGHT")
    totales_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.black),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    elements.append(totales_table)
    elements.append(Spacer(1, 3 * mm))

    # ── Clave de acceso (barcode representación texto) ────────────────────
    elements.append(HRFlowable(width="100%", thickness=0.5))
    elements.append(Spacer(1, 1 * mm))
    elements.append(Paragraph(f"CLAVE DE ACCESO: {clave_acceso}", estilo_center))
    elements.append(Spacer(1, 1 * mm))
    elements.append(HRFlowable(width="100%", thickness=0.5))

    doc.build(elements)
    return buffer.getvalue()
