from __future__ import annotations

from shared.domain.value_objects.ecuador_identification import is_valid_cedula
from shared.errors import ValidationError


class Cedula:
    def __init__(self, value: str) -> None:
        value = (value or "").strip()
        if not self._is_valid(value):
            raise ValidationError("Cédula inválida")
        self.value = value

    @staticmethod
    def _is_valid(value: str) -> bool:
        return is_valid_cedula(value)

    def __str__(self) -> str:
        return self.value
