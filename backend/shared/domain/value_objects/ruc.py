from __future__ import annotations

"""
Value Object: Ecuadorian RUC.

Validates the check digit using the SRI algorithm for:
- Natural person (type 0-5): modulo 10
- Public entity   (type 6):  modulo 11 with public-entity coefficients
- Legal entity    (type 9):  modulo 11 with legal-entity coefficients
- Requires the complete 13-digit RUC used for invoicing.

Reference: https://www.sri.gob.ec/web/guest/RUC
"""
from shared.domain.value_objects.ecuador_identification import is_valid_ruc
from shared.errors import ValidationError


class RUC:
    def __init__(self, value: str) -> None:
        value = (value or "").strip()
        if not self._is_valid(value):
            raise ValidationError("RUC inválido")
        self.value = value

    # ── main validation ───────────────────────────────────────────────────────

    def _is_valid(self, ruc: str) -> bool:
        return is_valid_ruc(ruc)

    # ── comparison and representation ─────────────────────────────────────────

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"RUC({self.value!r})"

    def __eq__(self, other) -> bool:
        return self.value == (other.value if isinstance(other, RUC) else str(other))

    def __hash__(self) -> int:
        return hash(self.value)
