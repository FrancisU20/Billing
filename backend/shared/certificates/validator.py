from __future__ import annotations

import base64
import re
import unicodedata
from datetime import UTC, datetime

from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from shared.certificates.errors import (
    CertificateExpiredError,
    CertificateInvalidError,
    CertificateRucMismatchError,
    CertificateRucNotExtractableError,
    CertificateUntrustedIssuerError,
)
from shared.certificates.metadata import CertificateMetadata
from shared.domain.value_objects.ruc import RUC

MAX_CERTIFICATE_BYTES = 50 * 1024


def _normalize_issuer_name(value: str) -> str:
    without_accents = "".join(
        char
        for char in unicodedata.normalize("NFKD", value)
        if not unicodedata.combining(char)
    )
    normalized_words = re.findall(r"[A-Z0-9]+", without_accents.upper())
    return " ".join(normalized_words)


_ALLOWED_ISSUER_NAMES_RAW = (
    "BANCO CENTRAL DEL ECUADOR",
    "SECURITY DATA",
    "SECURITY DATA S.A.",
    "ANF",
    "DATIL",
)
ALLOWED_ISSUER_NAMES = tuple(
    sorted({_normalize_issuer_name(issuer) for issuer in _ALLOWED_ISSUER_NAMES_RAW})
)


class CertificateValidator:
    def validate_base64(
        self,
        *,
        certificate_b64: str,
        password: str,
        expected_ruc: str,
    ) -> CertificateMetadata:
        try:
            p12_bytes = base64.b64decode(certificate_b64, validate=True)
        except ValueError as exc:
            raise CertificateInvalidError("p12 base64 inválido") from exc

        if not p12_bytes or len(p12_bytes) > MAX_CERTIFICATE_BYTES:
            raise CertificateInvalidError("p12 vacío o excede el límite permitido")

        return self.validate_bytes(
            p12_bytes=p12_bytes,
            password=password,
            expected_ruc=expected_ruc,
        )

    def validate_bytes(
        self,
        *,
        p12_bytes: bytes,
        password: str,
        expected_ruc: str,
    ) -> CertificateMetadata:
        if not password:
            raise CertificateInvalidError("clave de certificado requerida")

        normalized_expected_ruc = str(RUC(expected_ruc))

        try:
            private_key, cert, _ = pkcs12.load_key_and_certificates(
                p12_bytes,
                password.encode("utf-8"),
            )
        except Exception as exc:
            raise CertificateInvalidError("p12 corrupto o clave incorrecta") from exc

        if private_key is None or cert is None:
            raise CertificateInvalidError("p12 sin llave privada o certificado")

        subject_ruc = _extract_ruc_from_name(cert.subject)
        if not subject_ruc:
            raise CertificateRucNotExtractableError()

        if subject_ruc != normalized_expected_ruc:
            raise CertificateRucMismatchError()

        expires_at = cert.not_valid_after_utc
        if expires_at < datetime.now(UTC):
            raise CertificateExpiredError(expires_at.isoformat())

        issuer = _issuer_name(cert.issuer)
        if not _issuer_allowed(issuer):
            raise CertificateUntrustedIssuerError(issuer)

        return CertificateMetadata(
            subject_ruc=subject_ruc,
            expires_at=expires_at,
            issuer=issuer,
        )


def _extract_ruc_from_name(name) -> str | None:
    candidates: list[str] = []
    for oid in (NameOID.SERIAL_NUMBER, NameOID.COMMON_NAME):
        candidates.extend(attr.value for attr in name.get_attributes_for_oid(oid))
    candidates.extend(attr.value for attr in name)

    for candidate in candidates:
        match = re.search(r"\b(\d{13})\b", candidate)
        if match:
            return match.group(1)
    return None


def _issuer_name(name) -> str:
    for oid in (NameOID.COMMON_NAME, NameOID.ORGANIZATION_NAME):
        attrs = name.get_attributes_for_oid(oid)
        if attrs:
            return attrs[0].value
    return ", ".join(attr.value for attr in name)


def _issuer_allowed(issuer: str) -> bool:
    return _normalize_issuer_name(issuer) in ALLOWED_ISSUER_NAMES
