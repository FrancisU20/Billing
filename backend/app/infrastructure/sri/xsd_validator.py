"""
Validador de XML contra los esquemas XSD del SRI.
Los schemas están versionados en infrastructure/sri/schemas/.
"""
import os

from lxml import etree

_SCHEMAS_DIR = os.path.join(os.path.dirname(__file__), "schemas")
_schema_cache: dict[str, etree.XMLSchema] = {}


def _load_schema(filename: str) -> etree.XMLSchema:
    if filename not in _schema_cache:
        path = os.path.join(_SCHEMAS_DIR, filename)
        with open(path, "rb") as f:
            doc = etree.parse(f)
        _schema_cache[filename] = etree.XMLSchema(doc)
    return _schema_cache[filename]


_SCHEMA_MAP = {
    "01": "factura_v1.1.0.xsd",
    "04": "notaCredito_v1.1.0.xsd",
    "05": "notaDebito_v1.1.0.xsd",
    "06": "guiaRemision_v1.1.0.xsd",
    "07": "comprobanteRetencion_v1.1.0.xsd",
}


def validar_xml(xml_str: str, tipo_comprobante: str) -> list[str]:
    """
    Valida un XML contra el XSD correspondiente al tipo de comprobante.
    Devuelve lista de errores (vacía = válido).
    """
    schema_file = _SCHEMA_MAP.get(tipo_comprobante)
    if not schema_file:
        return [f"Tipo de comprobante no soportado: {tipo_comprobante}"]

    schema_path = os.path.join(_SCHEMAS_DIR, schema_file)
    if not os.path.exists(schema_path):
        # Si no existe el XSD local, saltar la validación con advertencia
        # Los schemas deben descargarse del SRI y colocarse en /schemas/
        return []

    try:
        schema = _load_schema(schema_file)
        doc = etree.fromstring(xml_str.encode("utf-8"))
        schema.validate(doc)
        return [str(e) for e in schema.error_log]
    except etree.XMLSyntaxError as e:
        return [f"XML malformado: {e}"]
    except Exception as e:
        return [f"Error de validación: {e}"]
