from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class ClaveAcceso:
    """
    Clave de acceso de 49 dígitos requerida por el SRI.
    Formato: fechaEmision(8) + tipoComp(2) + ruc(13) + ambiente(1) +
             establecimiento(3) + puntoEmision(3) + secuencial(9) +
             codigoNumerico(8) + tipoEmision(1) + digitoVerificador(1)
    """
    value: str

    def __post_init__(self):
        if len(self.value) != 49 or not self.value.isdigit():
            raise ValueError(f"Clave de acceso inválida: {self.value}")

    @classmethod
    def generate(
        cls,
        fecha_emision: date,
        tipo_comprobante: str,
        ruc: str,
        ambiente: str,  # "1" pruebas, "2" producción
        establecimiento: str,
        punto_emision: str,
        secuencial: str,
        codigo_numerico: str,
        tipo_emision: str = "1",  # "1" normal
    ) -> "ClaveAcceso":
        fecha_str = fecha_emision.strftime("%d%m%Y")
        base = (
            f"{fecha_str}"
            f"{tipo_comprobante.zfill(2)}"
            f"{ruc.zfill(13)}"
            f"{ambiente}"
            f"{establecimiento.zfill(3)}"
            f"{punto_emision.zfill(3)}"
            f"{secuencial.zfill(9)}"
            f"{codigo_numerico.zfill(8)}"
            f"{tipo_emision}"
        )
        digito = cls._modulo11(base)
        return cls(base + str(digito))

    @staticmethod
    def _modulo11(valor: str) -> int:
        """Algoritmo módulo 11 del SRI para calcular el dígito verificador."""
        factores = [2, 3, 4, 5, 6, 7]
        suma = 0
        for i, digito in enumerate(reversed(valor)):
            suma += int(digito) * factores[i % len(factores)]
        residuo = 11 - (suma % 11)
        if residuo == 11:
            return 0
        if residuo == 10:
            return 1
        return residuo

    def __str__(self) -> str:
        return self.value
