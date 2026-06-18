from __future__ import annotations

"""
XAdES-BES enveloped signature, per SRI Ecuador Ficha Técnica (Anexo 14):
RSA-SHA1 + SHA1 digests + C14N 1.0 (REC-xml-c14n-20010315), firma enveloped.

SHA1/RSA-SHA1 is mandated by the SRI webservice spec, not a security choice here —
the document is sent to a fixed government validator that expects this exact
algorithm suite. `# nosec` / `# noqa: S324` mark every SHA1 usage for that reason.

Uses `etree.tostring(element, method="c14n")` (libxml2's classic C14N 1.0), NOT the
module-level `etree.canonicalize()` (which implements C14N 2.0/RFC 6931 — a
different, incompatible serialization the SRI spec does not ask for).
"""

import base64
import hashlib
from datetime import UTC, datetime
from uuid import uuid4

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.x509 import Certificate
from lxml import etree

_DS_NS = "http://www.w3.org/2000/09/xmldsig#"
_ETSI_NS = "http://uri.etsi.org/01903/v1.3.2#"
_C14N_ALGORITHM = "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"


def _ds(tag: str) -> str:
    return f"{{{_DS_NS}}}{tag}"


def _etsi(tag: str) -> str:
    return f"{{{_ETSI_NS}}}{tag}"


def _c14n(element: etree._Element) -> bytes:
    return etree.tostring(element, method="c14n")


def _sha1_b64(data: bytes) -> str:
    return base64.b64encode(hashlib.sha1(data).digest()).decode("ascii")  # nosec B324 - SRI XAdES-BES spec mandates SHA1, not a security control  # noqa: S324


def sign_xades_bes(xml_str: str, private_key: RSAPrivateKey, certificate: Certificate) -> str:
    root = etree.fromstring(xml_str.encode("utf-8"))  # noqa: S320 - our own xml_builder output, not external/untrusted input

    document_digest = _sha1_b64(_c14n(root))

    cert_der = certificate.public_bytes(serialization.Encoding.DER)
    cert_b64 = base64.b64encode(cert_der).decode("ascii")
    cert_digest = _sha1_b64(cert_der)

    suffix = uuid4().hex[:12]
    signature_id = f"Signature{suffix}"
    signed_properties_id = f"SignedProperties{suffix}"
    certificate_id = f"Certificate{suffix}"
    object_id = f"{signature_id}-Object"

    signing_time = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S%z")

    signed_properties = etree.Element(
        _etsi("SignedProperties"),
        nsmap={"etsi": _ETSI_NS, "ds": _DS_NS},
        Id=signed_properties_id,
    )
    signed_signature_properties = etree.SubElement(
        signed_properties, _etsi("SignedSignatureProperties")
    )
    etree.SubElement(signed_signature_properties, _etsi("SigningTime")).text = signing_time
    signing_certificate = etree.SubElement(signed_signature_properties, _etsi("SigningCertificate"))
    cert_el = etree.SubElement(signing_certificate, _etsi("Cert"))
    cert_digest_el = etree.SubElement(cert_el, _etsi("CertDigest"))
    etree.SubElement(cert_digest_el, _ds("DigestMethod"), Algorithm=f"{_DS_NS}sha1")
    etree.SubElement(cert_digest_el, _ds("DigestValue")).text = cert_digest
    issuer_serial = etree.SubElement(cert_el, _etsi("IssuerSerial"))
    etree.SubElement(
        issuer_serial, _ds("X509IssuerName")
    ).text = certificate.issuer.rfc4514_string()
    etree.SubElement(issuer_serial, _ds("X509SerialNumber")).text = str(certificate.serial_number)
    signed_data_object_properties = etree.SubElement(
        signed_properties, _etsi("SignedDataObjectProperties")
    )
    data_object_format = etree.SubElement(
        signed_data_object_properties, _etsi("DataObjectFormat"), ObjectReference="#comprobante"
    )
    etree.SubElement(data_object_format, _etsi("MimeType")).text = "text/xml"

    signed_properties_digest = _sha1_b64(_c14n(signed_properties))

    signed_info = etree.Element(_ds("SignedInfo"), nsmap={"ds": _DS_NS})
    etree.SubElement(signed_info, _ds("CanonicalizationMethod"), Algorithm=_C14N_ALGORITHM)
    etree.SubElement(signed_info, _ds("SignatureMethod"), Algorithm=f"{_DS_NS}rsa-sha1")

    reference_document = etree.SubElement(signed_info, _ds("Reference"), URI="#comprobante")
    transforms = etree.SubElement(reference_document, _ds("Transforms"))
    etree.SubElement(transforms, _ds("Transform"), Algorithm=f"{_DS_NS}enveloped-signature")
    etree.SubElement(reference_document, _ds("DigestMethod"), Algorithm=f"{_DS_NS}sha1")
    etree.SubElement(reference_document, _ds("DigestValue")).text = document_digest

    reference_properties = etree.SubElement(
        signed_info,
        _ds("Reference"),
        Type="http://uri.etsi.org/01903#SignedProperties",
        URI=f"#{signed_properties_id}",
    )
    etree.SubElement(reference_properties, _ds("DigestMethod"), Algorithm=f"{_DS_NS}sha1")
    etree.SubElement(reference_properties, _ds("DigestValue")).text = signed_properties_digest

    signature_value_bytes = private_key.sign(
        _c14n(signed_info),
        padding.PKCS1v15(),
        hashes.SHA1(),  # nosec B303 - SRI XAdES-BES spec mandates RSA-SHA1  # noqa: S303
    )

    signature = etree.Element(_ds("Signature"), nsmap={"ds": _DS_NS}, Id=signature_id)
    signature.append(signed_info)
    etree.SubElement(signature, _ds("SignatureValue")).text = base64.b64encode(
        signature_value_bytes
    ).decode("ascii")
    key_info = etree.SubElement(signature, _ds("KeyInfo"), Id=certificate_id)
    x509_data = etree.SubElement(key_info, _ds("X509Data"))
    etree.SubElement(x509_data, _ds("X509Certificate")).text = cert_b64
    signature_object = etree.SubElement(signature, _ds("Object"), Id=object_id)
    qualifying_properties = etree.SubElement(
        signature_object,
        _etsi("QualifyingProperties"),
        nsmap={"etsi": _ETSI_NS},
        Target=f"#{signature_id}",
    )
    qualifying_properties.append(signed_properties)

    root.append(signature)
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8").decode("utf-8")
