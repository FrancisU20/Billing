from __future__ import annotations

from shared.errors import ConflictError, NotFoundError


class ClientNotFoundError(NotFoundError):
    code = "CLIENT_NOT_FOUND"
    default_message = "El cliente no fue encontrado."


class ClientDuplicateIdentificationError(ConflictError):
    code = "CLIENT_DUPLICATE_IDENTIFICATION"
    default_message = "Ya existe un cliente con esa identificación."
