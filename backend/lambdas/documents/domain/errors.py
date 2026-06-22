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


class DocumentNotAuthorizedError(BusinessError):
    code = "DOCUMENT_NOT_AUTHORIZED"
    default_message = "Solo se pueden anular documentos autorizados."


class AnnulmentWindowExpiredError(BusinessError):
    code = "ANNULMENT_WINDOW_EXPIRED"
    default_message = (
        "El plazo para anular este documento ante el SRI ya venció. "
        "A partir de esta fecha solo se puede corregir con una nota de crédito."
    )


class ConsumerFinalCannotBeAnnulledError(BusinessError):
    code = "CONSUMER_FINAL_CANNOT_BE_ANNULLED"
    default_message = "Las facturas emitidas a Consumidor Final no se pueden anular ante el SRI."
