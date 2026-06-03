"""
Configuración de tarifas IVA desde SSM Parameter Store.
Permite actualizar la tarifa sin hacer deploy de CDK.

Parámetros SSM:
  /codelabs-billing/{env}/sri/iva_codigo_porcentaje  → "4" (15% actual)
  /codelabs-billing/{env}/sri/iva_tarifa             → "15"
"""
from aws_lambda_powertools.utilities import parameters

from app.shared.config import get_settings
from app.shared.logging import logger

settings = get_settings()

# Mapa oficial SRI: codigo_porcentaje → tarifa (%)
TARIFAS_IVA: dict[str, float] = {
    "0": 0.0,
    "2": 12.0,   # histórico
    "3": 14.0,   # histórico
    "4": 15.0,   # vigente desde 2024
    "6": 5.0,
    "8": 5.0,
    "10": 13.0,
}

_DEFAULT_CODIGO = "4"
_DEFAULT_TARIFA = 15.0


def get_iva_vigente() -> dict:
    """
    Retorna el IVA vigente configurado en SSM.
    Cachea 5 minutos con Lambda Powertools.
    Fallback a los defaults si SSM no está disponible (dev local).
    """
    if settings.is_local:
        return {"codigo_porcentaje": _DEFAULT_CODIGO, "tarifa": _DEFAULT_TARIFA}

    try:
        prefijo = f"/codelabs-billing/{settings.env}/sri"
        codigo = parameters.get_parameter(f"{prefijo}/iva_codigo_porcentaje") or _DEFAULT_CODIGO
        tarifa_str = parameters.get_parameter(f"{prefijo}/iva_tarifa") or str(_DEFAULT_TARIFA)
        return {
            "codigo_porcentaje": str(codigo).strip(),
            "tarifa": float(tarifa_str),
        }
    except Exception as e:
        logger.warning("No se pudo leer IVA de SSM — usando default 15%", extra={"error": str(e)})
        return {"codigo_porcentaje": _DEFAULT_CODIGO, "tarifa": _DEFAULT_TARIFA}


def tarifa_para_codigo(codigo_porcentaje: str) -> float:
    """Devuelve el porcentaje numérico para un codigo_porcentaje del SRI."""
    return TARIFAS_IVA.get(codigo_porcentaje, _DEFAULT_TARIFA)
