from __future__ import annotations

"""
Access key (clave de acceso) generator for SRI Ecuador electronic documents.

Structure (49 digits):
  fechaEmision(8)  + tipoComprobante(2) + ruc(13) + tipoAmbiente(1)
  + establ(3)      + punto(3)           + secuencial(9)
  + codigoNumerico(8) + tipoEmision(1)  + digitoVerificador(1)

tipoAmbiente: "1" = pruebas, "2" = producción (Tabla 4, Ficha Tecnica SRI)
tipoEmision:  "1" = emisión normal
"""

from datetime import date


def _modulo_11(digits: str) -> int:
    weights = [2, 3, 4, 5, 6, 7]
    total = sum(int(d) * weights[i % 6] for i, d in enumerate(reversed(digits)))
    remainder = total % 11
    if remainder == 0:
        return 0
    if remainder == 1:
        return 1
    return 11 - remainder


def generate_access_key(
    *,
    issued_at: date,
    doc_type: str,
    ruc: str,
    environment: str,
    serie: str,
    sequential: int,
    numeric_code: str,
    emission_type: str = "1",
) -> str:
    # Tabla 4, Ficha Tecnica SRI: 1=Pruebas, 2=Produccion. Invertido hasta
    # 2026-06-18 — causaba que celcer.sri.gob.ec (ambiente de pruebas) recibiera
    # claves de acceso marcadas como "produccion", lo que el SRI rechazaba.
    env_digit = "1" if environment == "testing" else "2"
    estab = serie[:3]
    punto = serie[3:]
    body = (
        issued_at.strftime("%d%m%Y")
        + doc_type
        + ruc
        + env_digit
        + estab
        + punto
        + str(sequential).zfill(9)
        + numeric_code
        + emission_type
    )
    if len(body) != 48:
        raise ValueError(f"access_key body has unexpected length {len(body)}: {body!r}")
    check = _modulo_11(body)
    return body + str(check)
