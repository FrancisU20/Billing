from __future__ import annotations

import base64
import datetime
import hashlib
import unittest

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID
from lxml import etree

from lambdas.invoice_processor.signing import sign_xades_bes

_NS = {"ds": "http://www.w3.org/2000/09/xmldsig#", "etsi": "http://uri.etsi.org/01903/v1.3.2#"}


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


class SignXadesBesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.private_key, self.certificate = _self_signed_certificate()
        self.xml = (
            '<factura id="comprobante" version="1.1.0">'
            "<infoTributaria><ruc>1792146739001</ruc></infoTributaria>"
            "</factura>"
        )

    def test_signature_value_validates_against_public_key(self) -> None:
        signed = sign_xades_bes(self.xml, self.private_key, self.certificate)
        root = etree.fromstring(signed.encode("utf-8"))

        signed_info = root.find(".//ds:Signature/ds:SignedInfo", _NS)
        signature_value_b64 = root.findtext(".//ds:SignatureValue", namespaces=_NS)

        self.private_key.public_key().verify(
            base64.b64decode(signature_value_b64),
            etree.tostring(signed_info, method="c14n"),
            padding.PKCS1v15(),
            hashes.SHA1(),  # nosec B303 - verifying the same legacy algorithm SRI mandates  # noqa: S324
        )

    def test_document_digest_matches_document_without_signature(self) -> None:
        signed = sign_xades_bes(self.xml, self.private_key, self.certificate)
        root = etree.fromstring(signed.encode("utf-8"))

        signature_el = root.find(".//ds:Signature", _NS)
        digest_value = root.findtext(
            './/ds:Reference[@URI="#comprobante"]/ds:DigestValue', namespaces=_NS
        )

        root.remove(signature_el)
        expected_digest = base64.b64encode(
            hashlib.sha1(etree.tostring(root, method="c14n")).digest()  # nosec B303 - SRI spec  # noqa: S324
        ).decode("ascii")

        self.assertEqual(digest_value, expected_digest)

    def test_includes_xades_qualifying_properties(self) -> None:
        signed = sign_xades_bes(self.xml, self.private_key, self.certificate)
        root = etree.fromstring(signed.encode("utf-8"))

        signing_time = root.find(".//etsi:SignedProperties//etsi:SigningTime", _NS)
        self.assertIsNotNone(signing_time)
        self.assertTrue(signing_time.text)

    def test_original_document_content_is_preserved(self) -> None:
        signed = sign_xades_bes(self.xml, self.private_key, self.certificate)
        root = etree.fromstring(signed.encode("utf-8"))

        self.assertEqual(root.findtext("infoTributaria/ruc"), "1792146739001")


if __name__ == "__main__":
    unittest.main()
