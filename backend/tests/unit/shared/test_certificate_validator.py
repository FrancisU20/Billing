from __future__ import annotations

import base64
import unittest
from datetime import UTC, datetime, timedelta

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID

from shared.certificates.errors import (
    CertificateExpiredError,
    CertificateInvalidError,
    CertificateRucMismatchError,
    CertificateRucNotExtractableError,
    CertificateUntrustedIssuerError,
)
from shared.certificates.validator import MAX_CERTIFICATE_BYTES, CertificateValidator
from tests.unit.support import VALID_RUC

OTHER_VALID_RUC = "1790000001001"
NATURAL_PERSON_RUC = "1003368725001"
NATURAL_PERSON_CEDULA = "1003368725"


def _p12_b64(
    *,
    ruc: str | None = VALID_RUC,
    password: str = "secret",
    expires_delta: timedelta = timedelta(days=365),
    issuer_name: str = "Security Data",
) -> str:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject_attrs = [x509.NameAttribute(NameOID.COMMON_NAME, "Empresa Test")]
    if ruc is not None:
        subject_attrs.append(x509.NameAttribute(NameOID.SERIAL_NUMBER, ruc))
    subject = x509.Name(subject_attrs)
    issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, issuer_name)])
    now = datetime.now(UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=2))
        .not_valid_after(now + expires_delta)
        .sign(key, hashes.SHA256())
    )
    p12 = pkcs12.serialize_key_and_certificates(
        name=b"tenant-certificate",
        key=key,
        cert=certificate,
        cas=None,
        encryption_algorithm=serialization.BestAvailableEncryption(password.encode("utf-8")),
    )
    return base64.b64encode(p12).decode("ascii")


class CertificateValidatorTests(unittest.TestCase):
    def test_valid_p12_returns_metadata(self) -> None:
        metadata = CertificateValidator().validate_base64(
            certificate_b64=_p12_b64(),
            password="secret",
            expected_ruc=VALID_RUC,
        )

        self.assertEqual(metadata.subject_ruc, VALID_RUC)
        self.assertEqual(metadata.issuer, "Security Data")

    def test_valid_p12_accepts_normalized_issuer_name(self) -> None:
        metadata = CertificateValidator().validate_base64(
            certificate_b64=_p12_b64(issuer_name="Security Data S.A."),
            password="secret",
            expected_ruc=VALID_RUC,
        )

        self.assertEqual(metadata.issuer, "Security Data S.A.")

    def test_wrong_password_raises_invalid(self) -> None:
        with self.assertRaises(CertificateInvalidError):
            CertificateValidator().validate_base64(
                certificate_b64=_p12_b64(),
                password="wrong",
                expected_ruc=VALID_RUC,
            )

    def test_expired_certificate_raises_expired(self) -> None:
        with self.assertRaises(CertificateExpiredError):
            CertificateValidator().validate_base64(
                certificate_b64=_p12_b64(expires_delta=timedelta(days=-1)),
                password="secret",
                expected_ruc=VALID_RUC,
            )

    def test_ruc_mismatch_raises_mismatch(self) -> None:
        with self.assertRaises(CertificateRucMismatchError):
            CertificateValidator().validate_base64(
                certificate_b64=_p12_b64(ruc=VALID_RUC),
                password="secret",
                expected_ruc=OTHER_VALID_RUC,
            )

    def test_untrusted_issuer_raises_untrusted_issuer(self) -> None:
        with self.assertRaises(CertificateUntrustedIssuerError):
            CertificateValidator().validate_base64(
                certificate_b64=_p12_b64(issuer_name="Untrusted CA"),
                password="secret",
                expected_ruc=VALID_RUC,
            )

    def test_issuer_substring_match_does_not_mark_certificate_as_trusted(self) -> None:
        with self.assertRaises(CertificateUntrustedIssuerError):
            CertificateValidator().validate_base64(
                certificate_b64=_p12_b64(issuer_name="BANFRAUD CA"),
                password="secret",
                expected_ruc=VALID_RUC,
            )

    def test_natural_person_p12_with_cedula_matches_ruc(self) -> None:
        metadata = CertificateValidator().validate_base64(
            certificate_b64=_p12_b64(ruc=NATURAL_PERSON_CEDULA),
            password="secret",
            expected_ruc=NATURAL_PERSON_RUC,
        )

        self.assertEqual(metadata.subject_ruc, NATURAL_PERSON_RUC)

    def test_natural_person_p12_with_cedula_mismatch_raises_mismatch(self) -> None:
        with self.assertRaises(CertificateRucMismatchError):
            CertificateValidator().validate_base64(
                certificate_b64=_p12_b64(ruc=NATURAL_PERSON_CEDULA),
                password="secret",
                expected_ruc=OTHER_VALID_RUC,
            )

    def test_ruc_not_extractable_raises_not_extractable(self) -> None:
        with self.assertRaises(CertificateRucNotExtractableError):
            CertificateValidator().validate_base64(
                certificate_b64=_p12_b64(ruc=None),
                password="secret",
                expected_ruc=VALID_RUC,
            )

    def test_certificate_over_size_limit_raises_invalid(self) -> None:
        oversized = base64.b64encode(b"0" * (MAX_CERTIFICATE_BYTES + 1)).decode("ascii")

        with self.assertRaises(CertificateInvalidError):
            CertificateValidator().validate_base64(
                certificate_b64=oversized,
                password="secret",
                expected_ruc=VALID_RUC,
            )


if __name__ == "__main__":
    unittest.main()
