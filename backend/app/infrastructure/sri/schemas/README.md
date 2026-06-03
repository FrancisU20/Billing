# Schemas XSD del SRI

Los schemas XSD deben descargarse del sitio oficial del SRI y colocarse en este directorio.

## Fuente oficial

https://www.sri.gob.ec/web/guest/facturacion-electronica

## Archivos requeridos

| Archivo | Descripción |
|---|---|
| `factura_v1.1.0.xsd` | Factura (tipo 01) |
| `notaCredito_v1.1.0.xsd` | Nota de crédito (tipo 04) |
| `notaDebito_v1.1.0.xsd` | Nota de débito (tipo 05) |
| `guiaRemision_v1.1.0.xsd` | Guía de remisión (tipo 06) |
| `comprobanteRetencion_v1.1.0.xsd` | Retención (tipo 07) |

## Nota

Si los XSD no están presentes, el validador omite la validación contra schema
y solo valida que el XML sea bien formado. Descargar los XSD antes de producción.
