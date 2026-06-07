from enum import Enum


class AmbienteSri(str, Enum):
    PRUEBAS    = "pruebas"
    PRODUCCION = "produccion"


class EstadoTenant(str, Enum):
    ACTIVO     = "activo"
    SUSPENDIDO = "suspendido"
    INACTIVO   = "inactivo"
