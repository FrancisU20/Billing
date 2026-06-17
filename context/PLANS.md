# Plans — Dominio

Estado: implementado, incluyendo campos `pruebas_*`, `dedicated_queue` y `self_service`.

## Lee Tambien Antes De Empezar

Leer estos archivos en orden antes de escribir codigo en este dominio:

| Archivo | Por que |
| --- | --- |
| `CLAUDE.md` | Reglas no negociables (seguridad, git) |
| `BACKEND.md` | Entidades globales, locks de unicidad, idempotencia |
| `FRONTEND.md` | Patrones de pantalla, design system para `features/plans/` |
| `TENANTS.md` | `plan_id` asignado a tenant, `plan_status` calculado |
| `ONBOARDING.md` | Uso de `pruebas_*`, `dedicated_queue` y `self_service` en el flujo de registro |
| `SUBSCRIPTIONS.md` | Pagos dLocal Go por ciclo de plan y reglas de planes gratuitos |

## Proposito

Catalogo comercial del SaaS. Define lo que puede hacer un tenant: cuantos documentos puede
emitir, que tipos de documento incluye, y el precio. Los planes son globales (no por tenant).

## Componentes

- Lambda: `backend/lambdas/plans/`
- DynamoDB: tabla `plans` (global)

## Frontend

- Publico: `frontend/features/marketing/components/PlansSection.tsx` dentro de la landing.
- Admin: `frontend/app/(app)/(superadmin)/plans/`

## Entidades

### Plan

Campos clave:

```
id                  UUID, PK — identidad interna
entity_type         "PLAN"
slug                identidad publica, inmutable despues de crear
name                nombre para mostrar
price               Decimal, serializado como string en API y DynamoDB
document_limit      int, -1 = ilimitado
limit_cycle         month | year
active              bool
order               int, para ordenar en pricing

# Onboarding y entorno de pruebas (sri_environment=pruebas):
pruebas_monthly_docs_limit   int (-1 = ilimitado)
pruebas_monthly_bulk_limit   int (-1 = ilimitado)
dedicated_queue              bool (Enterprise: queue SQS propia)
self_service                 bool (False = Enterprise, flujo "lead capture")

# Flags de tipos de documento incluidos:
includes_credit_notes        bool
includes_withholdings        bool
includes_delivery_notes      bool
includes_api                 bool

# Suscripcion SaaS:
# El monto de cobro sale de monthly_price/annual_price; dLocal Go no requiere
# IDs de precio por plan en DynamoDB.
```

### Reglas De Negocio

- `slug` es inmutable. Una vez creado el plan, el slug no cambia. Es la identidad publica
  que clientes y partners usan para referenciar el plan.
- `price` se modela como `Decimal` en Python y se serializa como string en API y DynamoDB.
  Nunca como float.
- `document_limit = -1` significa ilimitado (Enterprise).
- La unicidad de slug se garantiza con lock transaccional `PLAN_SLUG#{slug}`.
- Planes legacy pueden existir sin `entity_type = "PLAN"` o sin lock de slug. Los repositorios
  los tratan como validos; las migraciones verifican que el lock exista antes de crearlo.

### Endpoints Publicos vs Admin — Separacion Critica

Los endpoints publicos no tienen autorizacion. Esta separacion es de seguridad, no de UX:

**Publicos** (sin JWT, sin filtros aceptados):
- `GET /plans` — siempre `active=True`, ignora cualquier query param.
- `GET /plans/{slug}` — solo si el plan esta activo; 404 si existe pero esta inactivo.

**Superadmin** (JWT + superadmin, con filtros completos):
- `GET /superadmin/plans` — acepta filtros: `q`, `slug`, `status`, `limit_cycle`, `created_from/to`.
- `GET /superadmin/plans/{id}` — devuelve el plan aunque este inactivo.

El backend hardcodea `ListPlansQuery(status="active")` en el handler publico. No hay logica
condicional — son rutas distintas. Si se agrega un endpoint publico nuevo, debe seguir el
mismo patron: no aceptar `status` como parametro.

**En frontend**:
- `usePlans()` — sin parametros, llama `/plans`.
- `useAdminPlans(filters)` — con filtros, llama `/superadmin/plans`.
- `useAdminPlan(slug)` — llama `/superadmin/plans/{slug}`.

### Plan Status Calculado

`plan_status` del tenant (no del plan) se calcula en `Tenant.effective_plan_status(now)`:
- `"active"` si `plan_cycle_ends_at > now`
- `"expired"` si no

No se persiste. Cuando se agreguen facturas/emisiones, el agotamiento de `document_limit`
debe incorporarse al calculo, no a un campo persistido.

## API Contract

| Metodo | Ruta | Auth | Descripcion |
| --- | --- | --- | --- |
| GET | `/plans` | ninguna | lista activos, sin filtros |
| GET | `/plans/{slug}` | ninguna | detalle activo, 404 si inactivo |
| GET | `/superadmin/plans` | superadmin | lista con filtros |
| GET | `/superadmin/plans/{id}` | superadmin | detalle, incluye inactivos |
| POST | `/plans` | superadmin | crear plan |
| PATCH | `/plans/{id}` | superadmin | actualizar plan |
| PATCH | `/plans/{id}/status` | superadmin | activar/desactivar |

## DynamoDB Schema

Tabla: `plans`. PK = `id` (sin SK).

```
Plan:
  id            = "{uuid}"
  entity_type   = "PLAN"
  slug          = "profesional"
  active        = True
  ...

Slug lock:
  id            = "PLAN_SLUG#profesional"
  entity_type   = "PLAN_SLUG_LOCK"
  plan_id       = "{uuid}"
```

`plans` usa scan completo sin paginacion en `list()`. Aceptable mientras el catalogo
sea < 100 planes. No replicar este patron para entidades de alta cardinalidad.

## Errores De Dominio

- `PlanNotFoundError`
- `PlanNotActiveError` — cuando se asigna plan a tenant
- `SlugAlreadyExistsError`

## Catalogo — Valores Por Plan (seed `v0001_seed_plans`)

| slug | document_limit | pruebas_monthly_docs_limit | pruebas_monthly_bulk_limit | dedicated_queue | self_service |
| --- | --- | --- | --- | --- | --- |
| free | 20 | 20 | 0 | false | true |
| basic | 50 | 50 | 0 | false | true |
| pyme | 300 | 200 | 50 | false | true |
| pro | 1000 | 500 | 200 | false | true |
| enterprise | -1 | -1 | -1 | true | false |

`self_service=false` (solo Enterprise) no oculta el plan del catalogo publico — `GET /plans`
sigue devolviendolo. Significa que `POST /onboarding/otp/confirm` con ese `plan_id` toma la rama
"lead capture" en vez de crear el tenant (ver `ONBOARDING.md`).

## Deuda Tecnica

- El scan completo de `plans` en `list()` no escala si el catalogo crece. Si se agregan
  planes de largo plazo o promocionales con alta rotacion, evaluar paginacion.
