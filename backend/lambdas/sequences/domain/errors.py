from __future__ import annotations

from shared.errors import BusinessError, ConflictError, NotFoundError


class EstablishmentNotFoundError(NotFoundError):
    code = "ESTABLISHMENT_NOT_FOUND"
    default_message = "El establecimiento no fue encontrado."


class EstablishmentCodeExistsError(ConflictError):
    code = "ESTABLISHMENT_CODE_EXISTS"
    default_message = "Ya existe un establecimiento con ese código."


class EmissionPointNotFoundError(NotFoundError):
    code = "EMISSION_POINT_NOT_FOUND"
    default_message = "El punto de emisión no fue encontrado."


class EmissionPointCodeExistsError(ConflictError):
    code = "EMISSION_POINT_CODE_EXISTS"
    default_message = "Ya existe un punto de emisión con ese código en este establecimiento."


class EmissionPointCode099ReservedError(BusinessError):
    code = "EMISSION_POINT_099_RESERVED"
    default_message = "El código 099 está reservado para pruebas y no puede crearse manualmente."


class SequenceExhaustedError(BusinessError):
    code = "SEQUENCE_EXHAUSTED"
    default_message = (
        "El secuencial SRI para este punto de emisión alcanzó el máximo (999,999,999)."
    )


class SequenceAlreadyUsedError(ConflictError):
    code = "SEQUENCE_ALREADY_USED"
    default_message = (
        "No se puede modificar el secuencial inicial porque ya se emitieron "
        "documentos con este punto de emisión."
    )
