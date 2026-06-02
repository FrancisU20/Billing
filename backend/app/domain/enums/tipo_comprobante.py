from enum import StrEnum


class TipoComprobante(StrEnum):
    FACTURA = "01"
    LIQUIDACION_COMPRA = "03"
    NOTA_CREDITO = "04"
    NOTA_DEBITO = "05"
    GUIA_REMISION = "06"
    RETENCION = "07"
