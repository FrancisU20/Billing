# Products — Dominio

Estado: **Sprint 1 implementado. Sprint 2a (descuento % por producto) implementado.**

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
- `discount_percentage` (0-100, opcional, `Decimal` con 2 decimales) es el descuento
  comercial del producto. **No** se persiste en `to_invoice_snapshot()` — se lee en vivo
  al emitir (igual que `unit_price`/`iva_rate`), nunca se "congela" en facturas pasadas.
  Sprint 2a (este sprint) solo agrega el campo + CRUD; la resolucion automatica en el
  facturador y la validacion de techo server-side quedan para Sprint 2c (ver
  `## Deuda Tecnica`).

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
- Accion de creacion rapida desde la pantalla de emision, oculta detras de "Añadir"
  para no sobrecargar la busqueda.
- Al seleccionar producto, se autollenan codigo, descripcion, precio unitario e IVA.
- El usuario puede editar cantidad/descuento antes de emitir. El descuento usa un
  input reutilizable que permite ingresar valor exacto o porcentaje, pero el payload
  fiscal conserva el descuento como valor absoluto.

## Deuda Tecnica

- Sprint 2b: campana de descuento global por tenant (`GET/PUT /products/discount-campaign`,
  singleton `PK=TENANT#{id}` `SK=DISCOUNT_CAMPAIGN` con `active: bool` + `percentage:
  Decimal`, roles `owner|admin`, sin fechas de inicio/fin en este alcance). Vive en la
  Lambda `products` (no Lambda nueva) porque el dueño del tenant administra su propia
  campana — `Tenant` es solo superadmin (`AUTH.md`), no es el lugar correcto.
- Sprint 2c: en `EmitDocumentScreen`, pre-llenar el `DiscountInput` de cada linea con
  `max(producto.discount_percentage, campana.percentage si activa)`. **Backend**: extender
  `InvoiceProductSnapshot` (`i_product_catalog.py`) con `discount_percentage`, nuevo puerto
  `IDiscountCampaignPort.get_active(tenant_id)` inyectado en `EmitDocumentUseCase`, y en
  `_compute_totals` validar `discount <= gross * max(snapshot.discount_percentage,
  campaign.percentage si activa) / 100` para **toda linea** (con o sin `product_id`) — esto
  cierra el riesgo de que una API enterprise futura evada el techo combinando descuentos o
  evitando mandar `product_id`. Decision tomada: el backend es la fuente de verdad del techo,
  no el frontend (mismo principio que ya aplica a `unit_price`/`iva_rate`: el snapshot del
  producto siempre gana sobre lo que mande el cliente).
- Sprint 2d: override auditado del techo (`override_discount_ceiling: bool` +
  `override_reason: str` obligatorio si es `True`) para descuentos ad-hoc legitimos que no
  estan ligados a la campana. Solo `owner|admin` puede activarlo (403 si lo intenta un rol
  inferior). Se audita via `shared/audit/writer.py` (mismo mecanismo que ya usan
  `clients`/`products`/`plans`/`tenants`, `documents` no lo usa hoy — se suma solo para
  este caso, no para toda mutacion de `Document`). Nunca se salta `discount <= gross`
  (piso fiscal no negociable, ni con override).
- Sprint 2e (opcional): RIDE muestra precio original + % aplicado + precio final por
  linea, para reforzar confianza ante el comprador. No bloqueante para el alcance fiscal.
- Movimientos de inventario (`IN`, `OUT`, `ADJUSTMENT`, `REVERSAL`) y descuento atomico de
  stock al emitir documento autorizado o al confirmar emision, segun decision contable.
- Paquetes/membresias con composicion de items internos.
- Historial de precios por producto si se requiere auditoria comercial fuera del
  snapshot legal de factura.
