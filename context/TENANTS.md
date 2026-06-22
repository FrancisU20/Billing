# Tenants — Dominio

Estado: implementado.

## Lee Tambien Antes De Empezar

Leer estos archivos en orden antes de escribir codigo en este dominio:

| Archivo | Por que |
| --- | --- |
| `CLAUDE.md` | Reglas no negociables (seguridad, git) |
| `BACKEND.md` | Entidades globales, locks de unicidad, idempotencia, outbox |
| `FRONTEND.md` | Patrones de pantalla, design system para `features/tenants/` |
| `AUTH.md` | Todos los endpoints requieren rol `superadmin` |
| `PLANS.md` | `plan_id` se valida contra catalogo de planes activo |
| `SUBSCRIPTIONS.md` | Campos `dlocal_payer_id`/`subscription_status`, independientes de `status`/`plan_status` |

## Proposito

Gestiona las empresas (tenants) registradas en el SaaS. Un tenant es la unidad
de aislamiento del sistema: cada empresa tiene sus propios clientes, documentos y
configuracion. El superadmin administra tenants; los usuarios del tenant no pueden
ver ni modificar los datos de otros tenants.

## Componentes

- Lambda: `backend/lambdas/tenants/`
- DynamoDB: tabla `tenants` (global, no scoped)

## Frontend

- `frontend/features/tenants/`
- `frontend/app/(app)/(superadmin)/tenants/`
- `TenantDetailScreen` permite al superadmin reintentar el acceso owner inicial mediante
  `POST /tenants/{id}/onboarding/retry`.
- `TenantDashboardScreen` (home tenant): saludo "Bienvenido" + fecha/hora actual
  (`useNow`), metricas reales via `useDocumentsSummary` (`GET /documents/summary`, ver
  `INVOICES.md`) — emitidos, autorizados, con novedad, total autorizado — en fila junto a
  "Modulos" (Facturas/Notas de credito/Retenciones), y debajo progreso de autorizacion y
  card de "Limite del plan" (barra de progreso verde/ambar/rojo o badge "Ilimitado"). La
  gestion de certificado vive en "Mi empresa" (`CompanyScreen`), no en el dashboard. No
  tiene equivalente superadmin (ver "Dashboard Superadmin — Implementado" abajo).
- `CompanyScreen` (`/(app)/(tenant)/settings/company`, item de menu "Mi empresa") y
  `CompanyEditScreen` (`/settings/company/edit`) — hub de configuracion tenant. Agrupa:
  datos de empresa (resumen de solo lectura +
  `CompanyEditScreen` para `owner|admin`, reusa `TenantForm` en `mode="edit"` — mismo
  endpoint `PATCH /tenants/{id}` que ya permitia self-service, sin cambios de backend),
  `CertificateSection` reusado, y filas de navegacion a `EstablishmentsScreen` (sin
  cambios), `DiscountCampaignScreen` (sin cambios, ver `PRODUCTS.md`) y `BillingScreen`
  (sin cambios estructurales; ver `SUBSCRIPTIONS.md` para el ajuste de pago manual). Antes
  de este sprint, esos tres ultimos vivian como items sueltos del menu principal tenant.

## Entidades

### Tenant

Campos clave:

```
id                 UUID, PK
entity_type        "TENANT"
ruc                RUC del negocio (13 digitos Ecuador)
trade_name         nombre comercial
legal_name         razon social legal
address            direccion matriz (dirMatriz en XML SRI)
accounting_required bool — obligado a llevar contabilidad (obligadoContabilidad en infoTributaria)
status             active | suspended | inactive
plan_id            UUID del plan asignado
plan_cycle_ends_at ISO8601 — cuando vence el ciclo del plan
sri_environment    testing | production
certificate_secret_arn  ARN interno Secrets Manager (no sale en API)
cert_subject_ruc, cert_expires_at, cert_issuer, cert_uploaded_at
cert_expiry_alert_60_sent_at, cert_expiry_alert_30_sent_at
onboarding_completed_at
deleted            bool, soft delete

# Suscripcion SaaS (dLocal Go como pasarela, ver SUBSCRIPTIONS.md):
dlocal_payer_id      str | None  — payer_id guardado; habilita cobro automatico y retry-payment
subscription_status  str | None  — "active" | "expired" | "pending_payment" | "payment_failed" | None
pending_order_id     str | None  — order_id PAID aun no vinculado al tenant (Phase 1 de activacion);
                                   se limpia a None al completar activate_subscription()
```

### Maquina De Estados

```
active ──► suspended
active ──► inactive
suspended ──► active
suspended ──► inactive
inactive ──► active        (reactivacion por superadmin)
```

`inactive → suspended` no es valido. Primero `inactive → active`, luego `active → suspended`.
Permanecer en el mismo estado es valido (idempotente).

La regla vive en `Tenant.change_status()`, no solo en la UI.

### Reglas De Negocio

- `ruc` no se recicla. Si un tenant se da de baja (`inactive`), el RUC sigue bloqueado.
  Esto es por compliance: el RUC es identidad legal y los documentos emitidos quedan asociados.
- `plan_id` se valida contra un plan existente y activo antes de crear o reasignar.
- `inactive` puede reactivarse por superadmin. La UI no debe decir "definitivo" ni "irreversible".
- `DELETE /tenants/{id}` existe como soft delete en backend pero no esta expuesto en UI,
  porque una empresa conserva documentos con validez tributaria.

### Plan Status Calculado

`plan_status` no se persiste. Se calcula en lectura:

```python
Tenant.effective_plan_status(now) -> "active" | "expired"
```

Usa `plan_cycle_ends_at`. Si luego se agregan documentos emitidos, el agotamiento del
`document_limit` debe incorporarse aqui, no en un campo persistido.

## API Contract

Todos los endpoints requieren JWT superadmin salvo `GET /plans` que es publico
(ver `PLANS.md`).

| Metodo | Ruta | Descripcion |
| --- | --- | --- |
| GET | `/tenants` | lista con filtros paginada |
| POST | `/tenants` | crear tenant |
| GET | `/tenants/{id}` | detalle |
| PATCH | `/tenants/{id}` | actualizar |
| PATCH | `/tenants/{id}/status` | cambiar estado |
| POST | `/tenants/{id}/onboarding/retry` | re-encolar provisioning Cognito/email owner |
| POST | `/tenants/{id}/subscription/activate` | activar suscripcion `pending_payment` |
| POST | `/tenants/{id}/subscription/renew` | renovar ciclo con pago confirmado |
| POST | `/tenants/{id}/subscription/retry-payment` | reintentar tarjeta guardada (owner/admin) |
| DELETE | `/tenants/{id}` | soft delete (no expuesto en UI) |

## DynamoDB Schema

Tabla: `tenants`. PK = `id` (sin SK).

```
Tenant:
  id            = "{uuid}"
  entity_type   = "TENANT"
  ruc           = "179..."
  status        = "active"
  ...

RUC lock:
  id            = "RUC#179..."
  entity_type   = "TENANT_RUC_LOCK"
  tenant_id     = "{uuid}"
```

El lock `RUC#...` garantiza unicidad de RUC con `TransactWriteItems`. El GSI `ruc-index`
sirve para lookup, pero la unicidad real la impone el lock transaccional.

El lock NO se elimina en soft delete ni en inactivacion.

**Busqueda por RUC sin scan — evaluada y descartada:**
`ruc-index` tiene `PK=ruc` SIN sort key (porque el RUC es unico GLOBAL entre tenants, no
por tenant). DynamoDB exige `eq()` en partition key — `begins_with()` no es valido ahi, asi
que el mismo truco que se uso en `clients.identification` no aplica sin una GSI nueva
(partition key de baja cardinalidad + `ruc` como sort key, que es infra/deploy). El modo
"RUC exacto" en `TenantsFilters` se queda exacto via `get_by_ruc()` (que tambien usan
`CreateTenantUseCase`/onboarding para chequear duplicados — no se toca).

**Salto de pagina:** `TenantsListScreen` usa `useEagerPagedList` (camina todas las paginas
del Scan acotado y pagina local con salto real) en vez de `useCursorPagedList` — ver
`FRONTEND.md`.

**Acciones de fila** (`TenantListItem`): ojo (Ver) + `RowActionsMenu` con Editar y
Suspender/Reactivar (toggle segun `tenant.status`, via `tenantsApi.setStatus` +
`ConfirmDialog`, mismo patron que el toggle de `PlanListItem`) — ver `RowActionsMenu.tsx`
en `FRONTEND.md`. "Inactivar" (la transicion mas drastica) se queda solo en el detalle del
tenant, no en el listado — deliberado, no es la accion mas comun de la fila.

## Errores De Dominio

- `TenantNotFoundError`
- `RucAlreadyRegisteredError`
- `InvalidStatusTransitionError` — lanzado por `Tenant.change_status()` para transiciones no permitidas
- `PlanNotFoundError`, `PlanNotActiveError` — al asignar plan

## Edge Cases Y Trampas

- **inactive → suspended directo**: no esta permitido. La UI debe ocultar la opcion o mostrar
  error claro si el backend lo rechaza.
- **Reactivar tenant inactive**: la regla `inactive → active` existe. Si se pregunta si
  `inactive` es irreversible, la respuesta correcta es NO.
- **RUC lock permanente**: a diferencia del identification lock de clients (que se libera al
  borrar el cliente), el RUC de tenant nunca se libera. Esto es intencional por compliance.

## Dashboard Superadmin — Implementado

`GET /superadmin/dashboard` (Lambda `tenants`, `@require_superadmin`) agrega 3 fuentes de
solo lectura en un unico request — handler `_dashboard`, use case
`GetSuperadminDashboardUseCase` (`backend/lambdas/tenants/use_cases/`):

- `ITenantRepository.aggregate_dashboard_stats(now)`: un Scan completo de `tenants`
  (mismo costo que `count()`/`list()` admin — catalogo B2B chico), tallado en una sola
  pasada en Python: total, nuevos este mes, por `sri_environment`, por
  `subscription_status`, y por `plan_id` **solo entre tenants con
  `subscription_status == "active"`** (sirve a la vez para "plan mas vendido" y la base
  del MRR).
- `IPaymentReader.aggregate_revenue(now)` (en `tenants`, no en `subscriptions` — ver
  `BACKEND.md`/comentario en `plan_catalog.py` sobre independencia de bundles): Scan de
  `payments` con `status=PAID`, sumando `amount` (ya bruto, con markup — ver
  `SUBSCRIPTIONS.md`) por mes/año actual. Sin GSI global por fecha (solo
  `tenant-payments-index` por tenant) — Scan completo, **deuda tecnica**: sin techo a
  diferencia de `tenants` (revisar si el volumen de pagos crece mucho).
- `IPlanCatalog.get_pricing(plan_ids)`: precios de los planes con tenants activos
  (`get_item` por id, catalogo chico) — usado para "MRR estimado" (precio mensual o
  anual/12 segun `limit_cycle`, con markup) y el nombre del plan mas vendido.

Metricas expuestas (`SuperadminDashboardSummary.to_dict()`): `tenants_total`,
`tenants_new_this_month` (+ `tenants_new_this_month_trend_pct`), `tenants_by_environment`,
`memberships_active`/`memberships_inactive` (basado en `subscription_status == "active"`,
no en `tenant.status` ni en `effective_plan_status()` — son 3 campos distintos, ver
`Tenant` arriba), `revenue_this_month`/`revenue_this_year` (bruto, + `_trend_pct` cada
uno), `mrr_estimate` (bruto), `top_plan` (`{plan_id, name, tenant_count}` o `null` sin
tenants activos), `daily_revenue` (serie de 30 dias) y `recent_tenants` (top 5 mas
recientes).

**Decision explicita**: "clientes registrados" = tenants registrados (el cliente del
SaaS es la empresa tenant). El total de `clients` cruzando todos los tenants queda
deliberadamente afuera — no hay GSI global y sumarlo requeriria un Scan sin techo de la
tabla `clients` (a diferencia de `tenants`/`payments`, que son catalogos chicos B2B).

### Fase 2 — tendencias, grafico, distribucion, tenants recientes

Mismos 2 Scans de Fase 1 (`tenants`, `payments`), sin Scans nuevos — todo lo de abajo se
calculo extendiendo lo que ya se recorria:

- **Tendencias % (`_trend_pct` en `GetSuperadminDashboardUseCase`, logica de negocio, no
  de persistencia)**: solo en `revenue_this_month`, `revenue_this_year` y
  `tenants_new_this_month` — son los unicos 3 valores comparables contra un periodo
  anterior calculable en el mismo Scan (mes/año anterior via
  `current_ecuador_previous_month_utc_bounds`/`current_ecuador_previous_year_utc_bounds`
  en `shared/dates.py`). Devuelve `None` (no `0%`) cuando el periodo anterior fue 0 — evita
  division por cero y el falso mensaje "sin cambios". **Deliberadamente sin %** en
  `mrr_estimate`, `memberships_active`/`memberships_inactive` ni `tenants_by_environment`
  — son fotos del estado actual, sin snapshot historico para comparar honestamente.
- **`daily_revenue`** (`PaymentRevenueStats.daily_last_30_days`): 30 baldes por fecha civil
  Ecuador pre-inicializados en `Decimal("0.00")` (dias sin pagos salen en 0, no ausentes),
  acumulados en el mismo Scan `status=PAID` de `aggregate_revenue`.
- **`recent_tenants`** (`TenantAggregateStats.recent_tenants`): top 5 tenants mas nuevos
  por `created_at`, ordenados en memoria al final del mismo Scan de `aggregate_dashboard_stats`
  — **no** un feed generico de auditoria. La tabla `audit` es por-tenant (sin GSI global por
  tiempo); traer actividad de toda la plataforma ordenada por fecha necesitaria una GSI
  nueva (infra fuera de alcance) o un Scan sin techo de una tabla con retencion legal de 7
  años. "Actividad reciente" del mockup quedo acotada a tenants recientes por esa razon.
- Rango del grafico fijo en 30 dias (no interactivo) — el backend ya soporta
  parametrizar dias si se pide una vuelta futura.

Frontend: `features/tenants/screens/SuperadminDashboardScreen.tsx` +
`useSuperadminDashboard` + `tenantsApi.dashboardSummary()` — mismo patron que
`useDocumentsSummary`/`GET /documents/summary` del dashboard tenant. Item de menu
"Dashboard" al inicio de la navegacion superadmin. `TrendChart.tsx` (SVG propio sobre
`react-native-svg`, ya instalado — sin dependencia nueva; antes `RevenueChart.tsx`, renombrado
y generalizado con prop `formatValue?: (value: number) => string` cuando el dashboard tenant
lo reuso para graficar conteos de documentos en vez de montos — default sigue siendo
`formatCurrency`) y `DistributionBar.tsx` (barra de porcentaje etiquetada, con prop opcional
`formatValue?: (count: number) => string` por el mismo motivo, default `String(count)` para no
romper los usos existentes; mismo lenguaje visual que el `progressTrack`/`progressFill` inline
de `TenantDashboardScreen.tsx`, sin centralizar ese inline existente en este cambio — deuda
señalada abajo) viven en `features/tenants/components/`. `StatMetric` (compartido) ahora
acepta `trend?: { pct, label }` y `size?: 'md' | 'lg'` opcionales.

`DistributionBar` recibe `variant: BadgeVariant` (mismo vocabulario que `Badge`), no un
color suelto — evita que cada pantalla invente su propio color sin significado de estado
(la primera version uso `chart.primary`/`chart.secondary` para el ambiente SRI, sin
relacion con ningun otro lugar de la app). `TENANT_ENVIRONMENT_BADGE_VARIANT` (`features/tenants/constants.ts`) centraliza
produccion→`success`/pruebas→`warning` — usado por el dashboard y por el Badge de ambiente
SRI en `TenantDetailScreen.tsx` (antes `variant="accent"` plano, sin diferenciar pruebas de
produccion). El Badge de plan (`active`/`expired`) en esa misma fila sigue en `accent` —
queda fuera de alcance, no se tocó.

## Deuda Tecnica

- `tenants` lista con scan paginado + `FilterExpression`. Para queries de alta cardinalidad
  o dashboard, necesita endpoints agregados; los scans actuales son para listado admin.
- `GET /tenants` devuelve `total` (`Select=COUNT` sobre el mismo Scan, ver `BACKEND.md`)
  salvo que `q`/`ruc`/`plan_status` esten activos — esos se
  resuelven en Python (`plan_status` se computa en lectura, nunca se persiste). Mismo costo
  que `list()`; no resuelve la deuda de arriba, solo la extiende al conteo.
- `DistributionBar.tsx` duplica el lenguaje visual del `progressTrack`/`progressFill` inline
  ya existente en `TenantDashboardScreen.tsx` en vez de centralizarlo en un componente
  compartido — quedo fuera de alcance de la Fase 2 del dashboard superadmin. Ya tiene un
  tercer consumidor ("Top clientes" del dashboard tenant, ver `INVOICES.md`); sigue siendo
  oportunidad de unificar, ahora con mas urgencia al tener 3 lugares con el mismo patron.

## Deuda Solventada

- 2026-06-14: los metadatos de certificado se serializan sin exponer
  `certificate_secret_arn`.
- 2026-06-14: los umbrales de alerta de certificado se derivan de
  `CERTIFICATE_EXPIRY_ALERT_THRESHOLDS_DAYS`; la entidad ya no duplica condicionales 60/30.
- 2026-06-14: `POST /tenants/{id}/onboarding/retry` re-encola
  `TenantCreatedEvent` en outbox sin mutar el tenant, para recuperar provisioning Cognito
  o email de bienvenida fallido.
- 2026-06-14: el frontend conserva `onboarding_completed_at` y metadatos de certificado
  en `tenantSchema`, y expone la accion "Reintentar acceso inicial" desde el detalle
  superadmin.
