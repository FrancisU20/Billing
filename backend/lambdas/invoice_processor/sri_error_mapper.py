from __future__ import annotations

"""Normalize SRI business errors for persistence and UI display.

The SRI returns terse, uppercase technical messages and sometimes splits useful
context into ``informacionAdicional``. This module is the single translation
boundary: SOAP parsing keeps the raw values, use cases persist the normalized
shape, and the frontend can render stable user-facing fields.
"""

from dataclasses import dataclass

PERMANENT = "PERMANENT"
RETRYABLE = "RETRYABLE"


@dataclass(frozen=True)
class SriErrorDefinition:
    title: str
    user_message: str
    category: str
    classification: str = PERMANENT


_ERRORS: dict[str, SriErrorDefinition] = {
    "1": SriErrorDefinition(
        title="Servicio SRI temporalmente no disponible",
        user_message=(
            "El SRI no pudo procesar el comprobante en este momento. "
            "Se reintentará automáticamente."
        ),
        category="SRI_DISPONIBILIDAD",
        classification=RETRYABLE,
    ),
    "2": SriErrorDefinition(
        title="Servicio SRI temporalmente no disponible",
        user_message=(
            "El SRI no pudo validar el comprobante en este momento. Se reintentará automáticamente."
        ),
        category="SRI_DISPONIBILIDAD",
        classification=RETRYABLE,
    ),
    "35": SriErrorDefinition(
        title="Archivo no cumple estructura XML",
        user_message=(
            "El XML no cumple la estructura exigida por el SRI. "
            "Revisa la configuración fiscal del emisor y vuelve a emitir."
        ),
        category="XML",
    ),
    "39": SriErrorDefinition(
        title="Firma inválida",
        user_message=(
            "La firma electrónica del comprobante no fue aceptada por el SRI. "
            "Revisa el certificado digital configurado."
        ),
        category="FIRMA",
    ),
    "43": SriErrorDefinition(
        title="Firma inválida",
        user_message=(
            "La firma electrónica del comprobante no fue aceptada por el SRI. "
            "Revisa el certificado digital configurado."
        ),
        category="FIRMA",
    ),
    "45": SriErrorDefinition(
        title="Secuencial registrado",
        user_message=(
            "El SRI ya recibió un comprobante con esta serie y secuencial. "
            "Revisa la numeración del punto de emisión."
        ),
        category="SECUENCIAL",
    ),
    "52": SriErrorDefinition(
        title="Error en diferencias",
        user_message=(
            "El SRI encontró diferencias en los cálculos del comprobante. "
            "Revisa subtotales, descuentos e impuestos."
        ),
        category="CALCULOS",
    ),
    "65": SriErrorDefinition(
        title="Fecha de emisión extemporánea",
        user_message=(
            "El comprobante fue enviado fuera del plazo permitido por el SRI "
            "para su fecha de emisión."
        ),
        category="FECHA_EMISION",
    ),
    "69": SriErrorDefinition(
        title="Identificación del receptor",
        user_message=(
            "El SRI no reconoce la identificación del comprador. Para Consumidor Final "
            "debe usarse tipo 07 e identificación 9999999999999."
        ),
        category="RECEPTOR",
    ),
    "70": SriErrorDefinition(
        title="Ambiente de procesamiento no disponible",
        user_message=(
            "El ambiente de procesamiento del SRI no está disponible. "
            "Se reintentará automáticamente."
        ),
        category="SRI_DISPONIBILIDAD",
        classification=RETRYABLE,
    ),
}


def _clean(value: str | None) -> str:
    return " ".join((value or "").strip().split())


def _normalize_code(code: str | None) -> str:
    cleaned = _clean(code)
    return cleaned.lstrip("0") or cleaned


def normalize_sri_error(
    *, code: str | None, message: str | None = None, additional_info: str | None = None
) -> dict:
    normalized_code = _normalize_code(code)
    raw_message = _clean(message)
    raw_additional_info = _clean(additional_info)
    definition = _ERRORS.get(normalized_code)

    title = definition.title if definition else raw_message or "Error SRI no clasificado"
    user_message = definition.user_message if definition else title
    if raw_additional_info:
        user_message = f"{user_message} Detalle SRI: {raw_additional_info}"

    return {
        "code": normalized_code,
        "message": title,
        "user_message": user_message,
        "category": definition.category if definition else "NO_CLASIFICADO",
        "classification": definition.classification if definition else PERMANENT,
        "raw_message": raw_message,
        "additional_info": raw_additional_info or None,
    }


def classify(code: str | None) -> str:
    normalized = normalize_sri_error(code=code)
    return str(normalized["classification"])
