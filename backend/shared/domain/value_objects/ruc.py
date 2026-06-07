from __future__ import annotations
"""
Value Object: Ecuadorian RUC.

Validates the check digit using the SRI algorithm for:
- Natural person (type 0-5): modulo 10
- Public entity   (type 6):  modulo 11 with public-entity coefficients
- Legal entity    (type 9):  modulo 11 with legal-entity coefficients

Reference: https://www.sri.gob.ec/web/guest/RUC
"""
from shared.errors import ValidationError


class RUC:
    def __init__(self, value: str) -> None:
        value = (value or "").strip()
        if not self._is_valid(value):
            raise ValidationError("RUC inválido")
        self.value = value

    # ── main validation ───────────────────────────────────────────────────────

    def _is_valid(self, ruc: str) -> bool:
        if not ruc.isdigit() or len(ruc) not in (10, 13):
            return False
        third_digit = int(ruc[2])
        if third_digit < 6:
            return self._modulo10(ruc[:9], ruc[9])
        if third_digit == 6:
            return self._modulo11_public(ruc[:8], ruc[8])
        if third_digit == 9:
            return self._modulo11_legal(ruc[:9], ruc[9])
        return False

    # ── SRI algorithms ────────────────────────────────────────────────────────

    @staticmethod
    def _modulo10(base: str, check_digit: str) -> bool:
        coef = [2, 1, 2, 1, 2, 1, 2, 1, 2]
        total = sum(
            (v - 9 if v >= 10 else v)
            for v in (int(base[i]) * coef[i] for i in range(9))
        )
        expected = 0 if total % 10 == 0 else 10 - total % 10
        return expected == int(check_digit)

    @staticmethod
    def _modulo11_public(ruc: str, check_digit: str) -> bool:
        coef = [3, 2, 7, 6, 5, 4, 3, 2]
        total = sum(int(ruc[i]) * coef[i] for i in range(8))
        remainder = total % 11
        expected = 0 if remainder == 0 else 11 - remainder
        return expected == int(check_digit)

    @staticmethod
    def _modulo11_legal(ruc: str, check_digit: str) -> bool:
        coef = [4, 3, 2, 7, 6, 5, 4, 3, 2]
        total = sum(int(ruc[i]) * coef[i] for i in range(9))
        remainder = total % 11
        expected = 0 if remainder == 0 else 11 - remainder
        return expected == int(check_digit)

    # ── comparison and representation ─────────────────────────────────────────

    def __str__(self)  -> str:  return self.value
    def __repr__(self) -> str:  return f"RUC({self.value!r})"
    def __eq__(self, other) -> bool:
        return self.value == (other.value if isinstance(other, RUC) else str(other))
    def __hash__(self) -> int:  return hash(self.value)
