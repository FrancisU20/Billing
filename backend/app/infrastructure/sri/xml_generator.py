"""
Generador de XML para comprobantes electrónicos del SRI Ecuador.
Soporta: Factura (01), Nota Crédito (04), Nota Débito (05).
Fase 3 implementa Factura; los demás se agregan en fases posteriores.
"""
from lxml import etree

from app.application.schemas.factura import DatosFactura
from app.domain.value_objects.clave_acceso import ClaveAcceso


def generar_factura(
    datos: DatosFactura,
    clave_acceso: ClaveAcceso,
    ruc_emisor: str,
    razon_social_emisor: str,
    nombre_comercial_emisor: str,
    dir_matriz_emisor: str,
    establecimiento: str,
    punto_emision: str,
    secuencial: str,
    ambiente: str,  # "1" pruebas | "2" produccion
) -> str:
    """Genera el XML de una Factura conforme al esquema SRI versión 1.1.0."""

    nsmap = {}
    factura = etree.Element("factura", id="comprobante", version="1.1.0", nsmap=nsmap)

    # ── infoTributaria ────────────────────────────────────────────────────
    info_trib = etree.SubElement(factura, "infoTributaria")
    _txt(info_trib, "ambiente", ambiente)
    _txt(info_trib, "tipoEmision", "1")
    _txt(info_trib, "razonSocial", razon_social_emisor)
    _txt(info_trib, "nombreComercial", nombre_comercial_emisor)
    _txt(info_trib, "ruc", ruc_emisor)
    _txt(info_trib, "claveAcceso", str(clave_acceso))
    _txt(info_trib, "codDoc", "01")
    _txt(info_trib, "estab", establecimiento.zfill(3))
    _txt(info_trib, "ptoEmi", punto_emision.zfill(3))
    _txt(info_trib, "secuencial", secuencial.zfill(9))
    _txt(info_trib, "dirMatriz", dir_matriz_emisor)

    # ── infoFactura ───────────────────────────────────────────────────────
    info_fac = etree.SubElement(factura, "infoFactura")
    _txt(info_fac, "fechaEmision", datos.fecha_emision)
    _txt(info_fac, "dirEstablecimiento", datos.direccion_establecimiento)

    if datos.contribuyente_especial:
        _txt(info_fac, "contribuyenteEspecial", datos.contribuyente_especial)

    _txt(info_fac, "obligadoContabilidad", datos.obligado_contabilidad)
    _txt(info_fac, "tipoIdentificacionComprador", datos.tipo_identificacion_comprador)
    _txt(info_fac, "razonSocialComprador", datos.razon_social_comprador)
    _txt(info_fac, "identificacionComprador", datos.identificacion_comprador)

    if datos.direccion_comprador:
        _txt(info_fac, "direccionComprador", datos.direccion_comprador)

    _txt(info_fac, "totalSinImpuestos", _dec(datos.total_sin_impuestos))
    _txt(info_fac, "totalDescuento", _dec(datos.total_descuento))

    # totalConImpuestos — agrupado por codigo + codigoPorcentaje
    total_con_imp = etree.SubElement(info_fac, "totalConImpuestos")
    impuestos_totales = _agrupar_impuestos(datos)
    for (codigo, cod_pct), (base, valor) in impuestos_totales.items():
        ti = etree.SubElement(total_con_imp, "totalImpuesto")
        _txt(ti, "codigo", codigo)
        _txt(ti, "codigoPorcentaje", cod_pct)
        _txt(ti, "baseImponible", _dec(base))
        _txt(ti, "valor", _dec(valor))

    _txt(info_fac, "propina", _dec(datos.propina))
    _txt(info_fac, "importeTotal", _dec(datos.importe_total))
    _txt(info_fac, "moneda", datos.moneda)

    # pagos
    pagos_el = etree.SubElement(info_fac, "pagos")
    for pago in datos.pagos:
        p = etree.SubElement(pagos_el, "pago")
        _txt(p, "formaPago", pago.forma_pago)
        _txt(p, "total", _dec(pago.total))
        _txt(p, "plazo", str(pago.plazo))
        _txt(p, "unidadTiempo", pago.unidad_tiempo)

    # ── detalles ──────────────────────────────────────────────────────────
    detalles_el = etree.SubElement(factura, "detalles")
    for det in datos.detalles:
        d = etree.SubElement(detalles_el, "detalle")
        _txt(d, "codigoPrincipal", det.codigo_principal)
        if det.codigo_auxiliar:
            _txt(d, "codigoAuxiliar", det.codigo_auxiliar)
        _txt(d, "descripcion", det.descripcion)
        _txt(d, "cantidad", str(round(det.cantidad, 6)))
        _txt(d, "precioUnitario", str(round(det.precio_unitario, 6)))
        _txt(d, "descuento", _dec(det.descuento))
        _txt(d, "precioTotalSinImpuesto", _dec(det.precio_total_sin_impuesto))

        imps_el = etree.SubElement(d, "impuestos")
        for imp in det.impuestos:
            i = etree.SubElement(imps_el, "impuesto")
            _txt(i, "codigo", imp.codigo)
            _txt(i, "codigoPorcentaje", imp.codigo_porcentaje)
            _txt(i, "tarifa", _dec(imp.tarifa))
            _txt(i, "baseImponible", _dec(imp.base_imponible))
            _txt(i, "valor", _dec(imp.valor))

    # ── infoAdicional ─────────────────────────────────────────────────────
    if datos.info_adicional or datos.email_comprador:
        info_ad = etree.SubElement(factura, "infoAdicional")
        if datos.email_comprador:
            ca = etree.SubElement(info_ad, "campoAdicional")
            ca.set("nombre", "email")
            ca.text = datos.email_comprador
        if datos.info_adicional:
            for nombre, valor in datos.info_adicional.items():
                ca = etree.SubElement(info_ad, "campoAdicional")
                ca.set("nombre", nombre)
                ca.text = str(valor)

    return etree.tostring(
        factura,
        pretty_print=False,
        xml_declaration=True,
        encoding="UTF-8",
    ).decode("utf-8")


# ── helpers ────────────────────────────────────────────────────────────────

def _txt(parent: etree._Element, tag: str, text: str) -> etree._Element:
    el = etree.SubElement(parent, tag)
    el.text = text
    return el


def _dec(value) -> str:
    return f"{float(value):.2f}"


def _agrupar_impuestos(datos: DatosFactura) -> dict:
    """Agrupa los impuestos de todos los detalles por (codigo, codigoPorcentaje)."""
    from collections import defaultdict
    from decimal import Decimal
    totales: dict[tuple, list] = defaultdict(lambda: [Decimal("0"), Decimal("0")])
    for det in datos.detalles:
        for imp in det.impuestos:
            key = (imp.codigo, imp.codigo_porcentaje)
            totales[key][0] += imp.base_imponible
            totales[key][1] += imp.valor
    return {k: (round(v[0], 2), round(v[1], 2)) for k, v in totales.items()}
