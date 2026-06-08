from __future__ import annotations

from enum import StrEnum


class IdentificationType(StrEnum):
    RUC = "ruc"
    CEDULA = "cedula"
    PASAPORTE = "pasaporte"
    EXTERIOR = "exterior"


class PersonType(StrEnum):
    NATURAL = "natural"
    JURIDICA = "juridica"


class ClientStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
