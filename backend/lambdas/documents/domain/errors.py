from __future__ import annotations

from shared.errors import BusinessError, NotFoundError


class DocumentNotFoundError(NotFoundError):
    code = "DOCUMENT_NOT_FOUND"
    default_message = "El documento no fue encontrado."


class CertificateNotUploadedError(BusinessError):
    code = "CERTIFICATE_NOT_UPLOADED"
    default_message = (
        "El tenant no tiene un certificado p12 cargado. "
        "Suba el certificado antes de emitir documentos."
    )


class DocumentLimitReachedError(BusinessError):
    code = "DOCUMENT_LIMIT_REACHED"
    default_message = (
        "Ha alcanzado el límite mensual de documentos de su plan. "
        "Actualice su plan para continuar emitiendo."
    )


class InvalidIssuedDateError(BusinessError):
    code = "INVALID_ISSUED_DATE"
    default_message = "La fecha de emisión no puede ser futura."


class RideNotAvailableError(BusinessError):
    code = "RIDE_NOT_AVAILABLE"
    default_message = "El RIDE solo está disponible para documentos autorizados."
