"""
Endpoint de configuración del sistema — valores que el frontend necesita para
operar correctamente (tarifas, catálogos SRI, etc.).
No requiere auth superadmin — cualquier usuario autenticado puede leerlos.
"""
from fastapi import APIRouter
from pydantic import BaseModel

from app.domain.constants.sri import FORMAS_PAGO, TIPOS_IDENTIFICACION
from app.infrastructure.sri.iva_config import TARIFAS_IVA, get_iva_vigente

router = APIRouter()


class IvaConfig(BaseModel):
    codigo_porcentaje: str
    tarifa: float
    descripcion: str


class SriConfig(BaseModel):
    iva_vigente: IvaConfig
    tarifas_disponibles: list[IvaConfig]
    formas_pago: list[dict]
    tipos_identificacion: list[dict]


@router.get("/sri", response_model=SriConfig)
def get_sri_config():
    """
    Devuelve la configuración SRI vigente para el frontend.
    El frontend usa este endpoint para pre-rellenar formularios
    con el IVA correcto sin hardcodear valores.
    """
    iva = get_iva_vigente()

    tarifas = [
        IvaConfig(codigo_porcentaje=cod, tarifa=tar, descripcion=f"IVA {tar:.0f}%")
        for cod, tar in TARIFAS_IVA.items()
    ]

    return SriConfig(
        iva_vigente=IvaConfig(
            codigo_porcentaje=iva["codigo_porcentaje"],
            tarifa=iva["tarifa"],
            descripcion=f"IVA {iva['tarifa']:.0f}% (vigente)",
        ),
        tarifas_disponibles=tarifas,
        formas_pago=FORMAS_PAGO,
        tipos_identificacion=TIPOS_IDENTIFICACION,
    )
