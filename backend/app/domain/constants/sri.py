"""
Catálogos oficiales del SRI Ecuador.
Fuente: Ficha Técnica de Comprobantes Electrónicos v2.21
"""

FORMAS_PAGO: list[dict] = [
    {"codigo": "01", "descripcion": "Sin utilización del sistema financiero (efectivo)"},
    {"codigo": "15", "descripcion": "Compensación de deudas"},
    {"codigo": "16", "descripcion": "Tarjeta de débito"},
    {"codigo": "17", "descripcion": "Dinero electrónico"},
    {"codigo": "18", "descripcion": "Tarjeta prepago"},
    {"codigo": "19", "descripcion": "Tarjeta de crédito"},
    {"codigo": "20", "descripcion": "Otros con utilización del sistema financiero"},
    {"codigo": "21", "descripcion": "Endoso de títulos"},
]

TIPOS_IDENTIFICACION: list[dict] = [
    {"codigo": "04", "descripcion": "RUC"},
    {"codigo": "05", "descripcion": "Cédula de identidad"},
    {"codigo": "06", "descripcion": "Pasaporte"},
    {"codigo": "07", "descripcion": "Consumidor final"},
    {"codigo": "08", "descripcion": "Identificación del exterior"},
]
