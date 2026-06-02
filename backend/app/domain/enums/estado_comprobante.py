from enum import StrEnum


class EstadoComprobante(StrEnum):
    DRAFT = "DRAFT"
    PENDING_VALIDATION = "PENDING_VALIDATION"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    XML_GENERATED = "XML_GENERATED"
    XML_SIGNED = "XML_SIGNED"
    SENT_TO_SRI = "SENT_TO_SRI"
    RECEIVED_BY_SRI = "RECEIVED_BY_SRI"
    RETURNED_BY_SRI = "RETURNED_BY_SRI"
    PENDING_AUTHORIZATION = "PENDING_AUTHORIZATION"
    AUTHORIZED = "AUTHORIZED"
    NOT_AUTHORIZED = "NOT_AUTHORIZED"
    PENDING_CANCELLATION = "PENDING_CANCELLATION"
    CANCELLED = "CANCELLED"
    EMAIL_PENDING = "EMAIL_PENDING"
    EMAIL_SENT = "EMAIL_SENT"
    EMAIL_FAILED = "EMAIL_FAILED"
    FAILED = "FAILED"
    RETRY_PENDING = "RETRY_PENDING"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED"

    # Transiciones válidas por estado
    VALID_TRANSITIONS: dict = {}  # poblado abajo


# Define qué transiciones son válidas para evitar estados inválidos
EstadoComprobante.VALID_TRANSITIONS = {
    EstadoComprobante.DRAFT: {EstadoComprobante.PENDING_VALIDATION},
    EstadoComprobante.PENDING_VALIDATION: {EstadoComprobante.VALIDATION_FAILED, EstadoComprobante.QUEUED},
    EstadoComprobante.QUEUED: {EstadoComprobante.PROCESSING},
    EstadoComprobante.PROCESSING: {EstadoComprobante.XML_GENERATED, EstadoComprobante.FAILED},
    EstadoComprobante.XML_GENERATED: {EstadoComprobante.XML_SIGNED, EstadoComprobante.FAILED},
    EstadoComprobante.XML_SIGNED: {EstadoComprobante.SENT_TO_SRI, EstadoComprobante.FAILED},
    EstadoComprobante.SENT_TO_SRI: {
        EstadoComprobante.RECEIVED_BY_SRI, EstadoComprobante.RETURNED_BY_SRI, EstadoComprobante.RETRY_PENDING,
    },
    EstadoComprobante.RECEIVED_BY_SRI: {EstadoComprobante.PENDING_AUTHORIZATION},
    EstadoComprobante.PENDING_AUTHORIZATION: {
        EstadoComprobante.AUTHORIZED, EstadoComprobante.NOT_AUTHORIZED, EstadoComprobante.RETRY_PENDING,
    },
    EstadoComprobante.AUTHORIZED: {EstadoComprobante.EMAIL_PENDING, EstadoComprobante.PENDING_CANCELLATION},
    EstadoComprobante.EMAIL_PENDING: {EstadoComprobante.EMAIL_SENT, EstadoComprobante.EMAIL_FAILED},
    EstadoComprobante.EMAIL_FAILED: {EstadoComprobante.EMAIL_PENDING},  # reintento manual
    EstadoComprobante.RETRY_PENDING: {
        EstadoComprobante.PROCESSING, EstadoComprobante.MANUAL_REVIEW_REQUIRED,
    },
    EstadoComprobante.PENDING_CANCELLATION: {EstadoComprobante.CANCELLED},
    # Estados terminales sin transición: VALIDATION_FAILED, NOT_AUTHORIZED, RETURNED_BY_SRI,
    # EMAIL_SENT, FAILED, CANCELLED, MANUAL_REVIEW_REQUIRED (requieren acción explícita)
}
