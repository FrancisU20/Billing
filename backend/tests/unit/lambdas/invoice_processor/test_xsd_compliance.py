from __future__ import annotations

"""
Valida el XML firmado contra el XSD real de Factura del SRI (no solo contra
nuestras propias aserciones). Esto hubiera detectado en CI el bug real de
Sprint 5 (`dirEstablecimiento` faltante) sin necesitar una prueba manual contra
`celcer.sri.gob.ec`.

`sri_xsd/factura_v1.xsd` es la version 1.0.0 publica (no hay 1.1.0 facil de
obtener fuera del portal del SRI), pero la secuencia de infoTributaria/
infoFactura/detalles que valida es la misma — 1.1.0 solo agrega elementos
opcionales nuevos (comercioExterior, etc.) que no usamos.
"""

import datetime
import unittest
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from lxml import etree

from lambdas.invoice_processor.signing import sign_xades_bes
from lambdas.invoice_processor.xml_builder import build_credit_note_xml, build_invoice_xml
from tests.unit.lambdas.invoice_processor.fixtures import make_document, make_invoice_tenant

_XSD_PATH = Path(__file__).parent / "sri_xsd" / "factura_v1.xsd"
_NOTA_CREDITO_XSD_PATH = Path(__file__).parent / "sri_xsd" / "nota_credito_v1.xsd"


def _self_signed_certificate():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "TEST")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.now(datetime.UTC))
        .not_valid_after(datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    return key, cert


class XsdComplianceTests(unittest.TestCase):
    def test_signed_invoice_validates_against_sri_xsd(self) -> None:
        document = make_document()
        tenant = make_invoice_tenant()
        private_key, certificate = _self_signed_certificate()

        xml = build_invoice_xml(document, tenant)
        signed = sign_xades_bes(xml, private_key, certificate)

        schema = etree.XMLSchema(etree.parse(str(_XSD_PATH)))
        root = etree.fromstring(signed.encode("utf-8"))

        self.assertTrue(
            schema.validate(root),
            msg="\n".join(str(e) for e in schema.error_log),
        )

    def test_xml_declaration_uses_double_quotes(self) -> None:
        # El parser del SRI rechaza la declaracion XML con comillas simples
        # (`version='1.0'`) que lxml emite por defecto, aunque sea valida por
        # spec — confirmado a mano contra celcer.sri.gob.ec el 2026-06-18.
        document = make_document()
        tenant = make_invoice_tenant()

        xml = build_invoice_xml(document, tenant)

        self.assertTrue(xml.startswith('<?xml version="1.0" encoding="UTF-8"?>'))

    def test_signed_xml_declaration_uses_double_quotes(self) -> None:
        document = make_document()
        tenant = make_invoice_tenant()
        private_key, certificate = _self_signed_certificate()

        xml = build_invoice_xml(document, tenant)
        signed = sign_xades_bes(xml, private_key, certificate)

        self.assertTrue(signed.startswith('<?xml version="1.0" encoding="UTF-8"?>'))


class NotaCreditoXsdComplianceTests(unittest.TestCase):
    """`sri_xsd/nota_credito_v1.xsd` es el XSD oficial 1.1.0 (descargado de
    sri.gob.ec, "XML y XSD Nota de Credito.zip") — a diferencia de
    `factura_v1.xsd` (1.0.0 reusado), este SI coincide con `_SCHEMA_VERSION`.
    Agregado tras un bug real: `_build_detalles` compartia `codigoPrincipal`
    (valido solo para Factura) entre Factura y Nota de Credito, y el SRI
    rechazaba toda Nota de Credito/anulacion con error de esquema. Los tests
    de estructura propios (`test_xml_builder.py`) no lo detectaban porque solo
    comparaban contra si mismos, nunca contra el esquema real del SRI.
    """

    def test_signed_credit_note_validates_against_sri_xsd(self) -> None:
        parent = make_document(document_id="parent-1")
        document = make_document(
            document_id="doc-2",
            doc_type="04",
            related_document_id="parent-1",
            credit_note_reason="Devolución de mercadería",
        )
        tenant = make_invoice_tenant()
        private_key, certificate = _self_signed_certificate()

        xml = build_credit_note_xml(document, tenant, parent)
        signed = sign_xades_bes(xml, private_key, certificate)

        schema = etree.XMLSchema(etree.parse(str(_NOTA_CREDITO_XSD_PATH)))
        root = etree.fromstring(signed.encode("utf-8"))

        self.assertTrue(
            schema.validate(root),
            msg="\n".join(str(e) for e in schema.error_log),
        )


if __name__ == "__main__":
    unittest.main()
