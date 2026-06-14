from __future__ import annotations

from shared.errors import BusinessError, ValidationError


class CertificateInvalidError(ValidationError):
    code = "CERTIFICATE_INVALID"
    default_message = "El certificado digital o su clave no son válidos."


class CertificateExpiredError(BusinessError):
    code = "CERTIFICATE_EXPIRED"
    default_message = "El certificado digital está caducado. Sube un certificado vigente."


class CertificateRucMismatchError(BusinessError):
    code = "CERTIFICATE_RUC_MISMATCH"
    default_message = "El RUC del certificado digital no coincide con el RUC registrado."


class CertificateUntrustedIssuerError(BusinessError):
    code = "CERTIFICATE_UNTRUSTED_ISSUER"
    default_message = "El emisor del certificado digital no está reconocido."


class CertificateRucNotExtractableError(BusinessError):
    code = "CERTIFICATE_RUC_NOT_EXTRACTABLE"
    default_message = "No se pudo leer el RUC dentro del certificado digital."
