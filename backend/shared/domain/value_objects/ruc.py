"""
Value Object: RUC ecuatoriano.

Valida el dígito verificador según el algoritmo del SRI para:
- Persona natural (tipo 0-5): módulo 10
- Entidad pública (tipo 6):   módulo 11 con coeficientes de entidad pública
- Persona jurídica (tipo 9):  módulo 11 con coeficientes de jurídica

Referencia: https://www.sri.gob.ec/web/guest/RUC
"""
from shared.errors import ValidationError


class RUC:
    def __init__(self, value: str) -> None:
        value = (value or "").strip()
        if not self._is_valid(value):
            raise ValidationError("RUC inválido")
        self.value = value

    # ── validación principal ──────────────────────────────────────────────────

    def _is_valid(self, ruc: str) -> bool:
        if not ruc.isdigit() or len(ruc) not in (10, 13):
            return False
        tercero = int(ruc[2])
        if tercero < 6:
            return self._modulo10(ruc[:9], ruc[9])
        if tercero == 6:
            return self._modulo11_publico(ruc[:8], ruc[8])
        if tercero == 9:
            return self._modulo11_juridico(ruc[:9], ruc[9])
        return False

    # ── algoritmos SRI ────────────────────────────────────────────────────────

    @staticmethod
    def _modulo10(cedula: str, digito: str) -> bool:
        coef = [2, 1, 2, 1, 2, 1, 2, 1, 2]
        suma = sum(
            (v - 9 if v >= 10 else v)
            for v in (int(cedula[i]) * coef[i] for i in range(9))
        )
        esperado = 0 if suma % 10 == 0 else 10 - suma % 10
        return esperado == int(digito)

    @staticmethod
    def _modulo11_publico(ruc: str, digito: str) -> bool:
        coef = [3, 2, 7, 6, 5, 4, 3, 2]
        suma = sum(int(ruc[i]) * coef[i] for i in range(8))
        res  = suma % 11
        esperado = 0 if res == 0 else 11 - res
        return esperado == int(digito)

    @staticmethod
    def _modulo11_juridico(ruc: str, digito: str) -> bool:
        coef = [4, 3, 2, 7, 6, 5, 4, 3, 2]
        suma = sum(int(ruc[i]) * coef[i] for i in range(9))
        res  = suma % 11
        esperado = 0 if res == 0 else 11 - res
        return esperado == int(digito)

    # ── comparación y representación ─────────────────────────────────────────

    def __str__(self)  -> str:  return self.value
    def __repr__(self) -> str:  return f"RUC({self.value!r})"
    def __eq__(self, other) -> bool:
        return self.value == (other.value if isinstance(other, RUC) else str(other))
    def __hash__(self) -> int:  return hash(self.value)
