from dataclasses import dataclass


@dataclass(frozen=True)
class Ruc:
    value: str

    def __post_init__(self):
        if not self.value.isdigit() or len(self.value) != 13:
            raise ValueError(f"RUC inválido: {self.value!r}")
        if not self._validate_checksum():
            raise ValueError(f"RUC con dígito verificador incorrecto: {self.value}")

    def _validate_checksum(self) -> bool:
        tipo = int(self.value[2])
        if tipo in (0, 1, 2, 3, 4, 5):
            return self._modulo11()
        if tipo == 6:
            return self._modulo11_public()
        if tipo == 9:
            return self._modulo11_juridic()
        return False

    def _modulo11(self) -> bool:
        coefs = [2, 1, 2, 1, 2, 1, 2, 1, 2]
        suma = sum(
            (d * c if (d := int(self.value[i]) * coefs[i]) < 10 else d - 9)
            for i, c in enumerate(coefs)
        )
        dv = 0 if suma % 10 == 0 else 10 - (suma % 10)
        return dv == int(self.value[9])

    def _modulo11_public(self) -> bool:
        coefs = [3, 2, 7, 6, 5, 4, 3, 2]
        suma = sum(int(self.value[i]) * c for i, c in enumerate(coefs))
        residuo = 11 - (suma % 11)
        dv = 0 if residuo in (11, 10) else residuo
        return dv == int(self.value[8])

    def _modulo11_juridic(self) -> bool:
        coefs = [4, 3, 2, 7, 6, 5, 4, 3, 2]
        suma = sum(int(self.value[i]) * c for i, c in enumerate(coefs))
        residuo = 11 - (suma % 11)
        dv = 0 if residuo in (11, 10) else residuo
        return dv == int(self.value[9])

    def __str__(self) -> str:
        return self.value
