from __future__ import annotations

"""
Builds the Factura (codDoc=01) XML per SRI Ecuador Ficha Técnica v1.1.0.

Pure function — no boto3, no I/O. Totals and access_key are already computed by
`EmitDocumentUseCase` (documents lambda, Sprint 3); this module only serializes
them into the XML structure the SRI expects.
"""

from collections import defaultdict
from decimal import Decimal

from lxml import etree

from lambdas.documents.domain.entities import Document
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


def build_invoice_xml(document: Document, tenant: Tenant) -> str:
    estab = document.serie[:3]
    punto = document.serie[3:6]
    ambiente = "2" if document.sri_environment == "testing" else "1"

    root = etree.Element("factura", id="comprobante", version=_SCHEMA_VERSION)

    info_tributaria = etree.SubElement(root, "infoTributaria")
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

    total_con_impuestos = etree.SubElement(info_factura, "totalConImpuestos")
    base_by_rate: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    valor_by_rate: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    for line in document.lines:
        base_by_rate[line.iva_rate] += line.subtotal
        valor_by_rate[line.iva_rate] += line.iva_amount
    for rate in sorted(base_by_rate):
        total_impuesto = etree.SubElement(total_con_impuestos, "totalImpuesto")
        _sub(total_impuesto, "codigo", "2")
        _sub(total_impuesto, "codigoPorcentaje", _IVA_CODIGO_PORCENTAJE[rate])
        _sub(total_impuesto, "baseImponible", _money(base_by_rate[rate]))
        _sub(total_impuesto, "valor", _money(valor_by_rate[rate]))

    _sub(info_factura, "propina", "0.00")
    _sub(info_factura, "importeTotal", _money(document.total))
    _sub(info_factura, "moneda", "DOLAR")

    pagos = etree.SubElement(info_factura, "pagos")
    pago = etree.SubElement(pagos, "pago")
    _sub(pago, "formaPago", document.payment_method)
    _sub(pago, "total", _money(document.total))

    detalles = etree.SubElement(root, "detalles")
    for line in document.lines:
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

    if document.buyer_email:
        info_adicional = etree.SubElement(root, "infoAdicional")
        _sub(info_adicional, "campoAdicional", document.buyer_email).set("nombre", "email")

    return etree.tostring(root, xml_declaration=True, encoding="UTF-8").decode("utf-8")
