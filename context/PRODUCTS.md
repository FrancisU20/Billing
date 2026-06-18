# Products — Dominio

Estado: **Sprint 1 en implementacion**.

Ultima actualizacion: 2026-06-18.

## Lee Tambien Antes De Empezar

| Archivo | Por que |
| --- | --- |
| `CLAUDE.md` | Reglas no negociables: tenant desde JWT, dinero con Decimal, deploy local solo si se pide |
| `BACKEND.md` | Clean Architecture, DynamoDB tenant-scoped, idempotencia y auditoria |
| `FRONTEND.md` | Estructura de features, rutas, componentes UI y patrones de pantalla |
| `INVOICES.md` | Las lineas de factura deben guardar snapshot legal para XML/RIDE |

## Proposito

Catalogo vendible del tenant. Un producto no es solo inventario fisico: tambien puede
representar servicios, paquetes, membresias u otros items facturables.

## Reglas De Negocio

- `product_id` (`id`) es el identificador interno estable. Nunca cambia.
- `sku` es el codigo comercial/SRI (`codigoPrincipal` en factura). Es editable, pero debe
  ser unico por tenant mientras el producto no este eliminado.
- La factura guarda snapshot de los campos usados en la linea. Cambiar SKU, nombre,
  precio o impuesto del producto no modifica documentos emitidos.
- `kind` clasifica el item vendible: `PRODUCT`, `SERVICE`, `PACKAGE`, `MEMBERSHIP`, `OTHER`.
- `stock_enabled=false` por defecto. Servicios, paquetes y membresias normalmente no
  manejan stock, pero no se bloquea para dejar flexibilidad operacional.
- Sprint 1 modela stock actual y umbral bajo. Movimientos/reservas/descuento automatico
  de stock quedan para Sprint 2.
- Soft delete: eliminar producto lo oculta y libera el lock de SKU. Facturas historicas
  conservan snapshot.

## DynamoDB

Tabla `products` tenant-scoped.

```text
PK = "TENANT#{tenant_id}"
SK = "PRODUCT#{product_id}"

Lock SKU:
PK = "TENANT#{tenant_id}"
SK = "PRODUCT_SKU#{sku_normalized}"
```

GSI `sku-index`:

```text
PK = tenant_id
SK = sku_normalized
```

Usos:

- `GET /products?sku=...` lookup exacto.
- `GET /products?q=...` lista por tenant con filtro in-memory sobre SKU/nombre/descripcion.

## HTTP

Tenant-scoped; `tenant_id` siempre viene del JWT.

```text
POST   /products
GET    /products
GET    /products/{id}
PATCH  /products/{id}
DELETE /products/{id}
```

Roles:

- `owner | admin`: crear, actualizar, eliminar.
- `owner | admin | viewer`: listar y consultar.

Mutaciones usan `X-Idempotency-Key`.

## Contrato Fiscal Con Invoices

`documents.lines[]` acepta `product_id` opcional. Si viene:

1. Backend valida que el producto exista y este `ACTIVE`.
2. Completa/valida snapshot de linea con `sku`, `name/description`, `unit_price`,
   `iva_rate`.
3. Persiste `product_id` en `InvoiceLine` solo como referencia informativa.
4. XML usa siempre snapshot (`codigoPrincipal`, `descripcion`, `precioUnitario`,
   `impuestos`) y no reconsulta el producto.

## Frontend

Rutas tenant:

```text
/products
/products/new
/products/{id}
/products/{id}/edit
```

Integracion en facturador:

- Selector/buscador de productos por linea.
- Accion de creacion rapida desde la pantalla de emision.
- Al seleccionar producto, se autollenan codigo, descripcion, precio unitario e IVA.
- El usuario puede editar cantidad/descuento antes de emitir.

## Deuda Tecnica

- Sprint 2: movimientos de inventario (`IN`, `OUT`, `ADJUSTMENT`, `REVERSAL`) y descuento
  atomico de stock al emitir documento autorizado o al confirmar emision, segun decision
  contable.
- Sprint 2: paquetes/membresias con composicion de items internos.
- Sprint 2: historial de precios por producto si se requiere auditoria comercial fuera
  del snapshot legal de factura.
