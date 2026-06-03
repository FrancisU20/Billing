"""
Firmador XAdES-BES para comprobantes electrónicos del SRI Ecuador.

El SRI exige firma digital XAdES-BES (XML Advanced Electronic Signature - Basic
Electronic Signature) conforme al estándar ETSI TS 101 903.

Flujo:
1. Cargar p12 desde S3 (usando contraseña de Secrets Manager)
2. Extraer clave privada RSA y cadena de certificados X.509
3. Construir el nodo <ds:Signature> con referencias al documento
4. Calcular digest SHA-1 del contenido a firmar
5. Firmar con clave privada RSA-SHA1
6. Insertar el nodo de firma en el XML

Nota: El SRI usa SHA-1 (no SHA-256) a pesar de ser obsoleto — es requisito normativo.
"""
import base64
import hashlib
import uuid
from datetime import UTC, datetime

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.serialization import Encoding, pkcs12
from lxml import etree

# Namespaces requeridos por XAdES-BES
NS_DS = "http://www.w3.org/2000/09/xmldsig#"
NS_ETSI = "http://uri.etsi.org/01903/v1.3.2#"
NS_MAP = {"ds": NS_DS, "xades": NS_ETSI}


def firmar_xml(xml_str: str, p12_bytes: bytes, p12_password: str) -> str:
    """
    Firma un XML con XAdES-BES usando el certificado p12 del emisor.

    Args:
        xml_str: XML a firmar (sin firma)
        p12_bytes: Contenido binario del archivo .p12
        p12_password: Contraseña del .p12

    Returns:
        XML firmado como string UTF-8
    """
    # 1. Cargar p12
    private_key, cert, chain = pkcs12.load_key_and_certificates(
        p12_bytes, p12_password.encode()
    )
    if cert is None:
        raise ValueError("El .p12 no contiene un certificado válido")

    # 2. Parsear el XML
    doc = etree.fromstring(xml_str.encode("utf-8"))

    # 3. Generar IDs únicos para las referencias
    sig_id = f"Signature{uuid.uuid4().hex[:8]}"
    cert_id = f"Certificate{uuid.uuid4().hex[:8]}"
    signed_props_id = f"SignedProperties{uuid.uuid4().hex[:8]}"
    ref_id = f"Reference{uuid.uuid4().hex[:8]}"

    # 4. Canonicalizar el documento para calcular el digest del contenido
    doc_canonical = _c14n(doc)
    doc_digest = _sha1_b64(doc_canonical)

    # 5. Construir el nodo <ds:Signature>
    signature = etree.SubElement(doc, f"{{{NS_DS}}}Signature", Id=sig_id)

    signed_info = etree.SubElement(signature, f"{{{NS_DS}}}SignedInfo")

    c14n_method = etree.SubElement(signed_info, f"{{{NS_DS}}}CanonicalizationMethod")
    c14n_method.set("Algorithm", "http://www.w3.org/TR/2001/REC-xml-c14n-20010315")

    sig_method = etree.SubElement(signed_info, f"{{{NS_DS}}}SignatureMethod")
    sig_method.set("Algorithm", "http://www.w3.org/2000/09/xmldsig#rsa-sha1")

    # Referencia al documento completo (sin la firma)
    ref_doc = etree.SubElement(signed_info, f"{{{NS_DS}}}Reference", Id=ref_id, URI="")
    transforms = etree.SubElement(ref_doc, f"{{{NS_DS}}}Transforms")
    t = etree.SubElement(transforms, f"{{{NS_DS}}}Transform")
    t.set("Algorithm", "http://www.w3.org/2000/09/xmldsig#enveloped-signature")
    dm_doc = etree.SubElement(ref_doc, f"{{{NS_DS}}}DigestMethod")
    dm_doc.set("Algorithm", "http://www.w3.org/2000/09/xmldsig#sha1")
    etree.SubElement(ref_doc, f"{{{NS_DS}}}DigestValue").text = doc_digest

    # Referencia a SignedProperties (XAdES)
    ref_sp = etree.SubElement(signed_info, f"{{{NS_DS}}}Reference", URI=f"#{signed_props_id}")
    ref_sp.set("Type", "http://uri.etsi.org/01903#SignedProperties")
    dm_sp = etree.SubElement(ref_sp, f"{{{NS_DS}}}DigestMethod")
    dm_sp.set("Algorithm", "http://www.w3.org/2000/09/xmldsig#sha1")
    # placeholder — se rellena después de construir SignedProperties
    sp_digest_el = etree.SubElement(ref_sp, f"{{{NS_DS}}}DigestValue")

    # 6. Construir KeyInfo con el certificado
    key_info = etree.SubElement(signature, f"{{{NS_DS}}}KeyInfo", Id=cert_id)
    x509_data = etree.SubElement(key_info, f"{{{NS_DS}}}X509Data")
    cert_der = cert.public_bytes(Encoding.DER)
    cert_b64 = base64.b64encode(cert_der).decode()
    etree.SubElement(x509_data, f"{{{NS_DS}}}X509Certificate").text = cert_b64

    # 7. Construir Object con XAdES QualifyingProperties
    obj = etree.SubElement(signature, f"{{{NS_DS}}}Object")
    qp = etree.SubElement(obj, f"{{{NS_ETSI}}}QualifyingProperties", Target=f"#{sig_id}")
    qp.set("xmlns:xades", NS_ETSI)
    sp = etree.SubElement(qp, f"{{{NS_ETSI}}}SignedProperties", Id=signed_props_id)

    # SignedSignatureProperties
    ssp = etree.SubElement(sp, f"{{{NS_ETSI}}}SignedSignatureProperties")
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    etree.SubElement(ssp, f"{{{NS_ETSI}}}SigningTime").text = now

    # SigningCertificate
    sc = etree.SubElement(ssp, f"{{{NS_ETSI}}}SigningCertificate")
    sc_cert = etree.SubElement(sc, f"{{{NS_ETSI}}}Cert")
    cd = etree.SubElement(sc_cert, f"{{{NS_ETSI}}}CertDigest")
    dm = etree.SubElement(cd, f"{{{NS_DS}}}DigestMethod")
    dm.set("Algorithm", "http://www.w3.org/2000/09/xmldsig#sha1")
    etree.SubElement(cd, f"{{{NS_DS}}}DigestValue").text = base64.b64encode(
        hashlib.sha1(cert_der).digest()
    ).decode()
    issuer_serial = etree.SubElement(sc_cert, f"{{{NS_ETSI}}}IssuerSerial")
    etree.SubElement(issuer_serial, f"{{{NS_DS}}}X509IssuerName").text = _issuer_name(cert)
    etree.SubElement(issuer_serial, f"{{{NS_DS}}}X509SerialNumber").text = str(cert.serial_number)

    # SignaturePolicyIdentifier — implied policy (SRI no requiere política específica)
    spi = etree.SubElement(ssp, f"{{{NS_ETSI}}}SignaturePolicyIdentifier")
    etree.SubElement(spi, f"{{{NS_ETSI}}}SignaturePolicyImplied")

    # Ahora calcular el digest de SignedProperties y rellenarlo
    sp_canonical = _c14n(sp)
    sp_digest_el.text = _sha1_b64(sp_canonical)

    # 8. Canonicalizar SignedInfo y firmar
    signed_info_canonical = _c14n(signed_info)
    signature_bytes = private_key.sign(
        signed_info_canonical,
        padding.PKCS1v15(),
        hashes.SHA1(),
    )
    sig_value_b64 = base64.b64encode(signature_bytes).decode()
    etree.SubElement(signature, f"{{{NS_DS}}}SignatureValue").text = sig_value_b64

    return etree.tostring(
        doc,
        pretty_print=False,
        xml_declaration=True,
        encoding="UTF-8",
    ).decode("utf-8")


def _c14n(element: etree._Element) -> bytes:
    """Canonicalización C14N del elemento (sin comments)."""
    from io import BytesIO
    buf = BytesIO()
    element.getroottree().write_c14n(buf, exclusive=False, with_comments=False, compression=0)
    # write_c14n opera sobre el árbol completo; usamos tostring con method="c14n" para un elemento
    return etree.tostring(element, method="c14n", exclusive=False, with_comments=False)


def _sha1_b64(data: bytes) -> str:
    return base64.b64encode(hashlib.sha1(data).digest()).decode()


def _issuer_name(cert: x509.Certificate) -> str:
    """Nombre del emisor en formato RFC 4514 (requerido por XAdES)."""
    return cert.issuer.rfc4514_string()
