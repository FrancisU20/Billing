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
- `TenantDashboardScreen` (home tenant): metricas reales via `useDocumentsSummary`
  (`GET /documents/summary`, ver `INVOICES.md`/`UX_REFACTOR.md` Sprint 5) — emitidos,
  autorizados, con novedad, total autorizado, progreso de autorizacion y card de "Limite
  del plan" (barra de progreso verde/ambar/rojo o badge "Ilimitado"). Tambien renderiza
  `CertificateSection` debajo del resumen. No tiene equivalente superadmin (ver "Dashboard
  Superadmin — Pendiente" abajo).
- `CompanyScreen` (`/(app)/(tenant)/settings/company`, item de menu "Mi empresa") y
  `CompanyEditScreen` (`/settings/company/edit`) — hub de configuracion tenant agregado en
  `UX_REFACTOR.md` Sprint 6. Agrupa: datos de empresa (resumen de solo lectura +
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

## Dashboard Superadmin — Pendiente

Cuando se implemente:

- Endpoint dedicado `GET /superadmin/dashboard` o similar.
- No calcular sumando scans del frontend; usar endpoint agregado backend.
- Metricas esperadas: tenants por estado, tenants por plan, ingresos estimados,
  clientes totales (si es viable sin scan caro por tenant).
- "Planes vendidos" = tenants activos agrupados por `plan_id`, no planes del catalogo.

## Deuda Tecnica

- `tenants` lista con scan paginado + `FilterExpression`. Para queries de alta cardinalidad
  o dashboard, necesita endpoints agregados; los scans actuales son para listado admin.
- `GET /tenants` devuelve `total` (`Select=COUNT` sobre el mismo Scan, ver `BACKEND.md` y
  `UX_REFACTOR.md` Sprint 1) salvo que `q`/`ruc`/`plan_status` esten activos — esos se
  resuelven en Python (`plan_status` se computa en lectura, nunca se persiste). Mismo costo
  que `list()`; no resuelve la deuda de arriba, solo la extiende al conteo.

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
