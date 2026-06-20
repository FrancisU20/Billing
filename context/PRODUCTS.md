# Products — Dominio

Estado: **Sprint 1 implementado. Sprint 2 completo: 2a (descuento % por producto), 2b
(campana de descuento global), 2c+2d (techo de descuento validado en backend +
resolucion en facturador + override auditado) y 2e (RIDE con % de descuento y precio
final por linea) implementados.**

Ultima actualizacion: 2026-06-19.

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
- `discount_percentage` (0-100, opcional, `Decimal` con 2 decimales) es el descuento
  comercial del producto. **No** se persiste en `to_invoice_snapshot()` — se lee en vivo
  al emitir (igual que `unit_price`/`iva_rate`), nunca se "congela" en facturas pasadas.
- Campana de descuento global (Sprint 2b): singleton por tenant (`active: bool` +
  `percentage: Decimal`, sin fechas de inicio/fin). La administra el propio tenant
  (`owner|admin`), no el superadmin — vive en la Lambda `products`, no en `Tenant`
  (`Tenant` es solo superadmin, ver `AUTH.md`).
- **Techo de descuento (Sprint 2c+2d, implementado en `documents`, no en `products`):**
  el detalle completo de la regla `max(producto%, campana%)`, la validacion server-side y
  el override auditado viven en `context/INVOICES.md` (seccion "Techo De Descuento Por
  Linea") porque tocan `EmitDocumentUseCase`/`_compute_totals`, no el dominio `products`.
  Aqui solo importa que `discount_percentage` (este archivo) y la campana (Sprint 2b) son
  los **inputs** de esa regla — ninguno de los dos aplica nada por si solo.

## DynamoDB

Tabla `products` tenant-scoped.

```text
PK = "TENANT#{tenant_id}"
SK = "PRODUCT#{product_id}"

Lock SKU:
PK = "TENANT#{tenant_id}"
SK = "PRODUCT_SKU#{sku_normalized}"

Campana de descuento (singleton, un item por tenant):
PK = "TENANT#{tenant_id}"
SK = "DISCOUNT_CAMPAIGN#default"
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
GET    /products/discount-campaign
PUT    /products/discount-campaign
```

Roles:

- `owner | admin`: crear, actualizar, eliminar producto; activar/configurar campana.
- `owner | admin | viewer`: listar y consultar producto; ver campana.

Mutaciones usan `X-Idempotency-Key`. `PUT /products/discount-campaign` es un upsert
(no hay distincion create/update — el primer `PUT` crea el singleton, los siguientes lo
actualizan con locking optimista por `version`).

`/products/discount-campaign` se resuelve **antes** que `/products/{id}` en el router del
handler (sin eso, `{id}` capturaria literalmente "discount-campaign" como si fuera un
`product_id`). Mismo cuidado aplica al registrar la ruta exacta en API Gateway
(`infra/stacks/api_stack.py`) antes/junto a la ruta parametrizada.

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
/settings/discount-campaign
```

`ProductsListScreen`/`ProductListItem`: `owner|admin` ven Editar + (Eliminar si `ACTIVE` |
Activar si `INACTIVE`, via `productsApi.setStatus` — mismo PATCH parcial existente, sin
endpoint nuevo); `viewer` no ve esas acciones ni "Nuevo producto" (gated por
`canWrite(role)`). `GET /products` devuelve `total` en el envelope (`Select=COUNT` Query
tenant-scoped) salvo que `q`/`sku` esten activos — ver `BACKEND.md` y `UX_REFACTOR.md`
Sprints 1/1.5.

`DiscountCampaignScreen` (`/settings/discount-campaign`): toggle activa/inactiva +
porcentaje, mismo patron de pantalla "singleton de ajustes" que `EstablishmentsScreen`.
Item propio en la navegacion tenant ("Descuento global"), no anidado bajo `/products`
porque conceptualmente es un ajuste del tenant, no un producto del catalogo.

Integracion en facturador:

- Selector/buscador de productos por linea.
- El selector muestra el descuento sugerido efectivo para factura: gana el mayor entre
  `discount_percentage` del producto y la campana global activa.
- Accion de creacion rapida desde la pantalla de emision, oculta detras de "Añadir"
  para no sobrecargar la busqueda.
- Al seleccionar producto, se autollenan codigo, descripcion, precio unitario e IVA.
- El usuario puede editar cantidad/descuento antes de emitir. La linea muestra fuente
  (`Catalogo`/`Campana`), porcentaje y monto sugerido; si el usuario modifica el descuento,
  la UI lo marca como edicion manual. El payload fiscal conserva el descuento como valor
  absoluto y backend valida el techo real.

## Deuda Tecnica

- Movimientos de inventario (`IN`, `OUT`, `ADJUSTMENT`, `REVERSAL`) y descuento atomico de
  stock al emitir documento autorizado o al confirmar emision, segun decision contable.
- Paquetes/membresias con composicion de items internos.
- Historial de precios por producto si se requiere auditoria comercial fuera del
  snapshot legal de factura.
