"""
Schemas Pydantic para validar los datos de entrada de una Factura (tipo 01).
Estos schemas validan el campo `datos` del comprobante antes de generar el XML.
"""
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, field_validator, model_validator


class ImpuestoDetalle(BaseModel):
    codigo: Literal["2", "3", "5"]          # 2=IVA, 3=ICE, 5=IRBPNR
    codigo_porcentaje: str                   # 0=0%, 2=12%, 3=14%, 4=15%, 8=5%, 10=13%, etc.
    tarifa: Decimal
    base_imponible: Decimal
    valor: Decimal

    @field_validator("base_imponible", "valor", "tarifa", mode="before")
    @classmethod
    def two_decimals(cls, v):
        return round(Decimal(str(v)), 2)


class DetalleFactura(BaseModel):
    codigo_principal: str
    descripcion: str
    cantidad: Decimal
    precio_unitario: Decimal
    descuento: Decimal = Decimal("0.00")
    precio_total_sin_impuesto: Decimal
    impuestos: list[ImpuestoDetalle]
    codigo_auxiliar: str | None = None

    @field_validator("cantidad", "precio_unitario", "descuento", "precio_total_sin_impuesto", mode="before")
    @classmethod
    def six_decimals(cls, v):
        return round(Decimal(str(v)), 6)

    @model_validator(mode="after")
    def validate_precio_total(self):
        expected = round(self.cantidad * self.precio_unitario - self.descuento, 2)
        actual = round(self.precio_total_sin_impuesto, 2)
        if abs(expected - actual) > Decimal("0.01"):
            raise ValueError(
                f"precio_total_sin_impuesto ({actual}) no coincide con "
                f"cantidad × precio_unitario - descuento ({expected})"
            )
        return self


class PagoFactura(BaseModel):
    forma_pago: str  # 01=efectivo, 16=transferencia, 19=tarjeta_credito, etc.
    total: Decimal
    plazo: int = 0
    unidad_tiempo: str = "dias"

    @field_validator("total", mode="before")
    @classmethod
    def two_decimals(cls, v):
        return round(Decimal(str(v)), 2)


class DatosFactura(BaseModel):
    """Estructura del campo `datos` para una Factura (tipo 01)."""

    # Receptor
    tipo_identificacion_comprador: Literal["04", "05", "06", "07", "08"]
    identificacion_comprador: str
    razon_social_comprador: str
    email_comprador: str | None = None
    direccion_comprador: str | None = None

    # Cabecera
    fecha_emision: str                       # formato dd/mm/yyyy
    obligado_contabilidad: Literal["SI", "NO"] = "NO"
    contribuyente_especial: str | None = None
    direccion_establecimiento: str = ""

    # Detalles
    detalles: list[DetalleFactura]

    # Totales
    total_sin_impuestos: Decimal
    total_descuento: Decimal = Decimal("0.00")
    importe_total: Decimal
    propina: Decimal = Decimal("0.00")
    moneda: str = "DOLAR"

    # Pagos
    pagos: list[PagoFactura]

    # Campos adicionales (opcional)
    info_adicional: dict[str, str] | None = None

    @field_validator("total_sin_impuestos", "total_descuento", "importe_total", "propina", mode="before")
    @classmethod
    def two_decimals(cls, v):
        return round(Decimal(str(v)), 2)

    @field_validator("detalles")
    @classmethod
    def at_least_one_detail(cls, v):
        if not v:
            raise ValueError("La factura debe tener al menos un detalle")
        return v

    @field_validator("pagos")
    @classmethod
    def at_least_one_pago(cls, v):
        if not v:
            raise ValueError("La factura debe tener al menos una forma de pago")
        return v
