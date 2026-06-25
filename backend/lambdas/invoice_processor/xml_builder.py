from __future__ import annotations

"""
Builds Factura (codDoc=01) y Nota de Credito (codDoc=04) XML per SRI Ecuador Ficha
Tecnica v1.1.0.

Pure functions — no boto3, no I/O. Totals y access_key ya estan calculados por
EmitDocumentUseCase/EmitCreditNoteUseCase (documents lambda); este modulo solo serializa
hacia la estructura XML que espera el SRI.
"""

from collections import defaultdict
from decimal import Decimal

from lxml import etree

from lambdas.documents.domain.entities import Document, InvoiceLine
from lambdas.tenants.domain.tenant import Tenant

_SCHEMA_VERSION = "1.1.0"

# SRI catalog (Tabla 19 Ficha Técnica) — codigoPorcentaje / tarifa por iva_rate interno
_IVA_CODIGO_PORCENTAJE = {"0": "0", "5": "5", "15": "4", "EXENTO": "7"}
_IVA_TARIFA = {"0": "0", "5": "5", "15": "15", "EXENTO": "0"}


def _sub(parent: etree._Element, tag: str, text: str) -> etree._Element:
    el = etree.SubElement(parent, tag)
    el.text = text
    return el


def _money(value: Decimal) -> str:
    return f"{value:.2f}"


def _build_total_con_impuestos(parent: etree._Element, lines: list[InvoiceLine]) -> None:
    total_con_impuestos = etree.SubElement(parent, "totalConImpuestos")
    base_by_rate: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    valor_by_rate: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    for line in lines:
        base_by_rate[line.iva_rate] += line.subtotal
        valor_by_rate[line.iva_rate] += line.iva_amount
    for rate in sorted(base_by_rate):
        total_impuesto = etree.SubElement(total_con_impuestos, "totalImpuesto")
        _sub(total_impuesto, "codigo", "2")
        _sub(total_impuesto, "codigoPorcentaje", _IVA_CODIGO_PORCENTAJE[rate])
        _sub(total_impuesto, "baseImponible", _money(base_by_rate[rate]))
        _sub(total_impuesto, "valor", _money(valor_by_rate[rate]))


def _build_detalles(root: etree._Element, lines: list[InvoiceLine]) -> None:
    detalles = etree.SubElement(root, "detalles")
    for line in lines:
        detalle = etree.SubElement(detalles, "detalle")
        _sub(detalle, "codigoPrincipal", line.code)
        _sub(detalle, "descripcion", line.description)
        _sub(detalle, "cantidad", str(line.quantity))
        _sub(detalle, "precioUnitario", _money(line.unit_price))
        _sub(detalle, "descuento", _money(line.discount))
        _sub(detalle, "precioTotalSinImpuesto", _money(line.subtotal))
        impuestos = etree.SubElement(detalle, "impuestos")
        impuesto = etree.SubElement(impuestos, "impuesto")
        _sub(impuesto, "codigo", "2")
        _sub(impuesto, "codigoPorcentaje", _IVA_CODIGO_PORCENTAJE[line.iva_rate])
        _sub(impuesto, "tarifa", _IVA_TARIFA[line.iva_rate])
        _sub(impuesto, "baseImponible", _money(line.subtotal))
        _sub(impuesto, "valor", _money(line.iva_amount))


def _build_info_tributaria(document: Document, tenant: Tenant) -> etree._Element:
    estab = document.serie[:3]
    punto = document.serie[3:6]
    # Tabla 4, Ficha Tecnica SRI: 1=Pruebas, 2=Produccion. Debe coincidir con el
    # mismo digito en la clave de acceso (domain/access_key.py).
    ambiente = "1" if document.sri_environment == "testing" else "2"

    info_tributaria = etree.Element("infoTributaria")
    _sub(info_tributaria, "ambiente", ambiente)
    _sub(info_tributaria, "tipoEmision", "1")
    _sub(info_tributaria, "razonSocial", tenant.legal_name)
    if tenant.trade_name:
        _sub(info_tributaria, "nombreComercial", tenant.trade_name)
    _sub(info_tributaria, "ruc", tenant.ruc)
    _sub(info_tributaria, "claveAcceso", document.access_key)
    _sub(info_tributaria, "codDoc", document.doc_type)
    _sub(info_tributaria, "estab", estab)
    _sub(info_tributaria, "ptoEmi", punto)
    _sub(info_tributaria, "secuencial", str(document.sequential).zfill(9))
    _sub(info_tributaria, "dirMatriz", tenant.address)
    return info_tributaria


def _build_info_adicional(root: etree._Element, document: Document) -> None:
    if document.buyer_email:
        info_adicional = etree.SubElement(root, "infoAdicional")
        _sub(info_adicional, "campoAdicional", document.buyer_email).set("nombre", "email")


def _serialize(root: etree._Element) -> str:
    # lxml's xml_declaration=True emite comillas simples (version='1.0'), que el
    # parser del SRI rechaza en la practica aunque sean validas por spec XML.
    # Se fuerza comillas dobles a mano.
    return '<?xml version="1.0" encoding="UTF-8"?>' + etree.tostring(root, encoding="unicode")


def build_invoice_xml(document: Document, tenant: Tenant) -> str:
    root = etree.Element("factura", id="comprobante", version=_SCHEMA_VERSION)
    root.append(_build_info_tributaria(document, tenant))

    info_factura = etree.SubElement(root, "infoFactura")
    _sub(info_factura, "fechaEmision", document.issued_at.strftime("%d/%m/%Y"))
    # dirEstablecimiento es obligatorio en el XSD del SRI. El dominio `sequences`
    # (Sprint 2) no guarda una dirección propia por establecimiento — solo
    # code/label — así que por ahora se reusa la dirección matriz del tenant.
    # Deuda técnica: agregar `address` a Establishment si se necesita una
    # dirección real por sucursal.
    _sub(info_factura, "dirEstablecimiento", tenant.address)
    _sub(info_factura, "obligadoContabilidad", "SI" if tenant.accounting_required else "NO")
    _sub(info_factura, "tipoIdentificacionComprador", document.buyer_id_type)
    _sub(info_factura, "razonSocialComprador", document.buyer_name)
    _sub(info_factura, "identificacionComprador", document.buyer_id)
    _sub(info_factura, "totalSinImpuestos", _money(document.subtotal))
    _sub(info_factura, "totalDescuento", _money(document.total_discount))

    _build_total_con_impuestos(info_factura, document.lines)

    _sub(info_factura, "propina", "0.00")
    _sub(info_factura, "importeTotal", _money(document.total))
    _sub(info_factura, "moneda", "DOLAR")

    pagos = etree.SubElement(info_factura, "pagos")
    pago = etree.SubElement(pagos, "pago")
    _sub(pago, "formaPago", document.payment_method)
    _sub(pago, "total", _money(document.total))

    _build_detalles(root, document.lines)
    _build_info_adicional(root, document)

    return _serialize(root)


def build_credit_note_xml(document: Document, tenant: Tenant, parent: Document) -> str:
    """Nota de Credito (codDoc=04). `parent` es la factura (01) AUTORIZADA que esta nota
    acredita — sus datos (numDocModificado/fechaEmisionDocSustento) se leen en vivo, nunca
    se duplican en el documento de la nota de credito. A diferencia de Factura, infoNota
    Credito no lleva bloque <pagos> (sin medio de pago: es una reversa, no un cobro).
    """
    root = etree.Element("notaCredito", id="comprobante", version=_SCHEMA_VERSION)
    root.append(_build_info_tributaria(document, tenant))

    info_nota_credito = etree.SubElement(root, "infoNotaCredito")
    _sub(info_nota_credito, "fechaEmision", document.issued_at.strftime("%d/%m/%Y"))
    _sub(info_nota_credito, "dirEstablecimiento", tenant.address)
    _sub(info_nota_credito, "tipoIdentificacionComprador", document.buyer_id_type)
    _sub(info_nota_credito, "razonSocialComprador", document.buyer_name)
    _sub(info_nota_credito, "identificacionComprador", document.buyer_id)
    _sub(info_nota_credito, "obligadoContabilidad", "SI" if tenant.accounting_required else "NO")
    _sub(info_nota_credito, "codDocModificado", parent.doc_type)
    _sub(info_nota_credito, "numDocModificado", parent.sequential_display)
    _sub(info_nota_credito, "fechaEmisionDocSustento", parent.issued_at.strftime("%d/%m/%Y"))
    _sub(info_nota_credito, "totalSinImpuestos", _money(document.subtotal))
    _sub(info_nota_credito, "valorModificacion", _money(document.total))
    _sub(info_nota_credito, "moneda", "DOLAR")

    _build_total_con_impuestos(info_nota_credito, document.lines)

    _sub(info_nota_credito, "motivo", document.credit_note_reason or "")

    _build_detalles(root, document.lines)
    _build_info_adicional(root, document)

    return _serialize(root)
