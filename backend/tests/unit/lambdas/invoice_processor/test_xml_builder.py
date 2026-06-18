from __future__ import annotations

import unittest
from decimal import Decimal

from lxml import etree

from lambdas.invoice_processor.xml_builder import build_invoice_xml
from tests.unit.lambdas.invoice_processor.fixtures import (
    ACCESS_KEY,
    make_document,
    make_invoice_tenant,
    make_line,
)


class BuildInvoiceXmlTests(unittest.TestCase):
    def test_includes_mandatory_info_tributaria_fields(self) -> None:
        document = make_document()
        tenant = make_invoice_tenant()

        xml = build_invoice_xml(document, tenant)
        root = etree.fromstring(xml.encode("utf-8"))

        self.assertEqual(root.tag, "factura")
        self.assertEqual(root.get("id"), "comprobante")
        self.assertEqual(root.findtext("infoTributaria/claveAcceso"), ACCESS_KEY)
        self.assertEqual(root.findtext("infoTributaria/ruc"), tenant.ruc)
        self.assertEqual(root.findtext("infoTributaria/estab"), "001")
        self.assertEqual(root.findtext("infoTributaria/ptoEmi"), "001")
        self.assertEqual(root.findtext("infoTributaria/secuencial"), "000000001")
        self.assertEqual(root.findtext("infoTributaria/ambiente"), "2")  # testing

    def test_includes_mandatory_dir_establecimiento(self) -> None:
        # Obligatorio en el XSD del SRI; sin esto el SRI rechaza con
        # "ARCHIVO NO CUMPLE ESTRUCTURA XML" (código 35) — confirmado contra
        # celcer.sri.gob.ec el 2026-06-18. `sequences` no guarda dirección propia
        # por establecimiento (deuda), así que se reusa la matriz del tenant.
        document = make_document()
        tenant = make_invoice_tenant(address="Av Siempre Viva 123")

        xml = build_invoice_xml(document, tenant)
        root = etree.fromstring(xml.encode("utf-8"))

        # Debe ir inmediatamente después de fechaEmision (orden del XSD).
        children = [el.tag for el in root.find("infoFactura")]
        self.assertEqual(children[0], "fechaEmision")
        self.assertEqual(children[1], "dirEstablecimiento")
        self.assertEqual(root.findtext("infoFactura/dirEstablecimiento"), "Av Siempre Viva 123")

    def test_production_environment_maps_to_ambiente_1(self) -> None:
        document = make_document(sri_environment="production")
        tenant = make_invoice_tenant()

        xml = build_invoice_xml(document, tenant)
        root = etree.fromstring(xml.encode("utf-8"))

        self.assertEqual(root.findtext("infoTributaria/ambiente"), "1")

    def test_groups_iva_totals_by_rate(self) -> None:
        document = make_document(
            lines=[
                make_line(iva_rate="15"),
                make_line(code="P2", iva_rate="0", iva_amount=Decimal("0.00")),
            ]
        )
        tenant = make_invoice_tenant()

        xml = build_invoice_xml(document, tenant)
        root = etree.fromstring(xml.encode("utf-8"))

        codigos = root.findall("infoFactura/totalConImpuestos/totalImpuesto/codigoPorcentaje")
        rates = {c.text for c in codigos}
        self.assertEqual(rates, {"4", "0"})  # 15% -> codigoPorcentaje "4", 0% -> "0"

    def test_detalle_per_line(self) -> None:
        document = make_document(lines=[make_line(), make_line(code="P2")])
        tenant = make_invoice_tenant()

        xml = build_invoice_xml(document, tenant)
        root = etree.fromstring(xml.encode("utf-8"))

        detalles = root.findall("detalles/detalle")
        self.assertEqual(len(detalles), 2)
        self.assertEqual(detalles[0].findtext("codigoPrincipal"), "P1")


if __name__ == "__main__":
    unittest.main()
