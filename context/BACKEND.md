# Backend — Arquitectura Y Patrones

Patrones de construccion transversales para Lambdas, DynamoDB, idempotencia, outbox
y migraciones. Las reglas de negocio de cada dominio viven en su propio archivo
(`AUTH.md`, `TENANTS.md`, `PLANS.md`, `CLIENTS.md`, `ONBOARDING.md`, `INVOICES.md`).

## Estructura

```text
backend/
  lambdas/
    _base/       # framework Lambda: handler, parser, response, permissions, idempotency
    auth/        # rutas publicas de login/refresh/logout/challenge
    tenants/     # empresas SaaS globales
    plans/       # catalogo comercial global
    clients/     # clientes por tenant
    products/    # catalogo vendible por tenant
    subscriptions/ # pagos dLocal Go (suscripcion SaaS del tenant)
    workers/     # outbox_relay, tenant_onboarding, email_notifications, migrations
  shared/        # errores, logging, fechas, db, value objects, audit, secrets, events, certificados
  migrations/    # migraciones DynamoDB versionadas
  tests/         # unittest + fakes

infra/
  stacks/        # CDK stacks
  config/        # dev, staging, prod
```

### Dominios Por Ambiente

Convencion environment-suffix flat (deja `wali.codelabsecuador.com` limpio en prod):

| Ambiente | Frontend | API |
| --- | --- | --- |
| dev | `wali-dev.codelabsecuador.com` | `api-wali-dev.codelabsecuador.com` |
| staging | `wali-staging.codelabsecuador.com` | `api-wali-staging.codelabsecuador.com` |
| prod | `wali.codelabsecuador.com` | `api-wali.codelabsecuador.com` |

Definidos en `infra/config/{env}.yaml` (`domain.frontend`/`domain.api`), usados por CDK para
CORS, CloudFront y Route 53. Dev no despliega CloudFront (`domain.enabled: false`).

Nota: certificados ACM para CloudFront se crean en `us-east-1`, aunque el resto del infra
esta en `sa-east-1`.

## Arquitectura Backend

Cada Lambda de negocio sigue Clean Architecture:

```text
handler.py      # presentacion: routeo, parseo, permisos, DI, ApiResponse
schemas.py      # DTO HTTP con Pydantic
domain/         # entidades, comandos, errores, repositorios ABC, eventos
use_cases/      # orquestacion; depende de interfaces, no de DynamoDB
infra/          # repositorios DynamoDB y adapters externos
```

Reglas:

- Dominio sin boto3, sin API Gateway, sin requests HTTP.
- Use cases no conocen implementaciones concretas.
- Handlers componen dependencias y cierran la respuesta HTTP.
- Repositorios concretos manejan persistencia, optimistic locking, auditoria, idempotencia
  y outbox cuando aplique.
- Mutaciones con side effects cierran todo en una sola transaccion DynamoDB:
  `entity + audit + idempotency completed + outbox`.
- Si un flujo coordina varios adapters en una misma transaccion, crear un adapter
  semantico de infraestructura. No componer diccionarios DynamoDB en handlers ni en
  interfaces de dominio. Referencia: `onboarding/infra/onboarding_commit_repository.py`.

`_base`:

| Archivo | Uso |
| --- | --- |
| `handler.py` | `@lambda_handler`, errores centralizados, logger |
| `sqs_handler.py` | workers SQS con partial batch failure |
| `parser.py` | `Request.from_event`, `parse`, path params, `Request.raw_body` |
| `permissions.py` | `require_role`, `require_superadmin` |
| `response.py` | contrato HTTP estandar |
| `idempotency.py` | reserva atomica por `X-Idempotency-Key` |

`shared`:

| Modulo | Uso |
| --- | --- |
| `errors.py` | jerarquia `AppError` con `code` y `default_message` |
| `dates.py` | parseo de rangos `created_from/to` |
| `db/base_repository.py` | tenant isolation, soft delete, list raw |
| `db/paginator.py` | cursor opaco base64 para DynamoDB |
| `db/limits.py` | defaults/cap de paginacion backend |
| `db/transactions.py` | helpers para razones de cancelacion `TransactWriteItems` |
| `audit/writer.py` | items de auditoria con TTL legal |
| `certificates` | validacion p12, metadata, Secrets Manager y umbrales de alerta |
| `domain/value_objects` | RUC, email, identificacion Ecuador |
| `domain/events` | DomainEvent, outbox, publisher |

### Fechas Y Timestamps

Regla de proyecto:

- Instantes tecnicos persistidos, TTLs, locks, caches, firmas externas y claves de ordenamiento
  se guardan como UTC/epoch para mantener comparaciones estables en DynamoDB y AWS.
- Fechas civiles/de negocio y todo timestamp que sale por API/correo/RIDE se presenta en
  `America/Guayaquil`.
- Usar `shared/dates.py` (`now_utc`, `now_ecuador`, `today_ecuador`,
  `isoformat_ecuador`, `parse_date_boundary`) en vez de crear conversiones locales.
- `created_from/to` con `YYYY-MM-DD` representa el dia civil Ecuador y se convierte a limites
  UTC antes de filtrar contra `created_at`.

## Contrato HTTP

Exito:

```json
{ "success": true, "data": {}, "error": null, "meta": { "request_id": "...", "timestamp": "..." } }
```

Error:

```json
{ "success": false, "data": null, "error": { "code": "TENANT_NOT_FOUND", "message": "La empresa no fue encontrada." }, "meta": {} }
```

Lista paginada:

```json
{
  "success": true,
  "data": { "items": [], "next_token": "eyJ...", "has_more": true, "total": 42 },
  "error": null,
  "meta": {}
}
```

Reglas:

- `next_token` es opaco. El frontend no lo decodifica.
- Los filtros via query params se validan en handler y se aplican en repositorio.
- Si se agregan listas nuevas, usar `DEFAULT_LIST_LIMIT` y `clamp_list_limit()` en backend.
- `total` (campo `total_items`/`total_pages` v2): viene de
  `ApiResponse.paginated(..., total=...)`. Se calcula con `BaseRepository._count_raw()`
  (Query tenant-scoped + `Select=COUNT`, sin transferir items) en `clients`/`products`,
  con `DynamoDocumentsRepository.count()` (mismo patron sobre el GSI) en `documents`, y
  con un Scan + `Select=COUNT` en `tenants` (aceptable solo por ser catalogo B2B chico,
  igual que `list()`). `total` es `None`/omitido cuando el filtro activo se resuelve en
  Python y no en DynamoDB (`q`, `sku`, `ruc`, `plan_status`) — un conteo DB-side en ese
  caso no reflejaria el resultado filtrado real. `plans` no necesita nada de esto: ya
  devuelve la lista completa y el frontend pagina localmente con `useLocalPagedItems`.

### Busqueda Por Identificador Sin Scan: GSI + `begins_with()`

Patron para cuando un dominio necesita "buscar por prefijo de un identificador estructurado
a escala" (cedula, RUC, SKU, etc.) sin caminar la tabla en memoria. Implementado en
`clients.identification` (`DynamoClientRepository._identification_prefix_raw()`/
`_identification_prefix_count()`, ver `CLIENTS.md`):

1. Requiere una GSI ya existente o nueva con `PK=tenant_id` (o el scope que corresponda) y
   `SK=<campo identificador>` — DynamoDB exige `eq()` en partition key, pero permite
   `begins_with()`/comparaciones en sort key porque la ordena lexicograficamente.
2. `Query` (no Scan) con `KeyConditionExpression: Key('tenant_id').eq(...) &
   Key('<campo>').begins_with(prefix)`. Mismo costo que un lookup exacto.
3. Para el total: el mismo Query con `Select=COUNT`, combinando el `FilterExpression` de
   los demas filtros estructurados (status, tipo, fechas) — siguen siendo DynamoDB-side,
   asi que el conteo queda exacto sin walk en Python.
4. **Antes de replicar este patron en otro campo, verificar dos cosas**: (a) que el metodo
   `get_by_*` exacto existente no se use en OTRO lado para validar duplicados (cambiar su
   semantica ahi rompe esa validacion — separar en un metodo nuevo, no reusar); (b) que la
   GSI tenga sort key (si el partition key es el propio identificador, como `ruc-index` en
   `tenants` por unicidad global, `begins_with()` no es valido ahi — se necesitaria una GSI
   nueva). Casos evaluados y descartados por esto: `products.sku` (duplicate-check
   acoplado, ver `PRODUCTS.md`), `tenants.ruc` (GSI sin sort key, ver `TENANTS.md`).

### `Request.raw_body`

`Request.from_event` expone tanto `body` (dict ya parseado) como `raw_body` (string
crudo del body, con el `base64` decodificado si aplica, antes del `json.loads`). Usar
`raw_body` cuando se necesite verificar una firma HMAC sobre el payload exacto que
envio el caller (ej. futuros webhooks dLocal) — re-serializar `body` con `json.dumps`
no reproduce los mismos bytes firmados.

## Auth — Resumen

El frontend nunca llama Cognito directamente. Se usa el **ID Token** como Bearer.
Claims relevantes: `custom:tenant_id`, `custom:role`, `custom:is_superadmin`.

Roles: `superadmin` (global), `owner` / `admin` / `viewer` (scoped al tenant).

Ver `AUTH.md` para el flujo SRP completo, endpoints, y trampas de tests.

## DynamoDB — Convenciones

### Entidades Globales

PK = `id` (UUID), sin SK. Tabla propia por dominio (`tenants`, `plans`).

Locks de unicidad en la misma tabla:

```text
id = "{TYPE}#{valor}"   entity_type = "{TYPE}_LOCK"
```

Ejemplo: `RUC#179...` para unicidad de RUC de tenant. El lock va en el mismo
`TransactWriteItems` que la entidad — no hay race condition.

### Entidades Tenant-Scoped

Convencion de `BaseRepository`:

```text
PK = "TENANT#{tenant_id}"
SK = "{PREFIX}#{entity_id}"
```

Los repositorios tenant-scoped reciben `tenant_id` en el constructor. Nunca viene del body.

### Paginacion

- DynamoDB aplica `Limit` antes de `FilterExpression`. Para filtros in-memory (`q`,
  `plan_status`) el repositorio puede necesitar caminar varias paginas.
- Usar `shared/db/limits.py` para defaults y cap de paginacion.

### Composicion Transaccional Entre Repositorios

Cuando un use case necesita escribir en **dos tablas distintas** en el mismo
`TransactWriteItems` (ej. Payment + Tenant), el repositorio expone un método
`save_transact_item(entity) -> dict` que retorna el dict `{"Put": {...}}` listo para
incluir en la transaccion, sin ejecutarla. El use case lo devuelve al handler, que lo
pasa como `extra_transact_items=[payment_transact]` en `repo.commit()`.

Ejemplo: `IPaymentRepository.save_transact_item(payment)` retorna el item Put del
Payment; `RetryPaymentUseCase.execute()` lo incluye en su tuple de retorno;
`tenants/handler.py` lo pasa al commit del Tenant para escritura atomica.

Repositorios que ya usan este patron:
- `IPaymentRepository.save_transact_item` (Payment → Payments table)
- `IPaymentReader.mark_applied_to_tenant` (update tenant_id en Payment → Payments table)

### Fix Conocido

Doble serializacion en `transact_write_items`: usar Python dicts puros con
`resource.meta.client`, no el resource de alto nivel.

## Idempotencia HTTP

Toda mutacion HTTP lleva `@idempotent` y exige `X-Idempotency-Key`.

La key queda ligada a tenant/global scope + method + path + hash canonico del body.

Estados: `IN_PROGRESS` → `COMPLETED` o `FAILED`.

Si ya completo: devuelve respuesta cacheada.
Si la misma key se reutiliza con otro body/path/method: `IDEMPOTENCY_KEY_REUSED`.

Para mutaciones transaccionales, `COMPLETED` se escribe en el mismo `TransactWriteItems`.

## Outbox Y Workers

Side effects no se ejecutan antes de confirmar la mutacion principal.

```text
HTTP handler -> use case -> repo.commit()
repo.commit() -> DynamoDB transaction: entity + audit + idempotency + outbox
OutboxRelayWorker -> SQS
Worker consumidor -> side effect idempotente
```

Workers actuales (disparados por outbox/SQS):

- `tenant_onboarding`: crea/sincroniza usuario Cognito.
- `email_notifications`: envia emails Brevo (bienvenida, OTP, lead enterprise, alerta
  de caducidad de certificado, avisos de suscripcion, estados de documentos SRI y
  entrega al comprador con XML autorizado + RIDE adjuntos).
- `outbox_relay`: publica eventos outbox a SQS.
- `migrations`: ejecuta migraciones de datos.

Si outbox marca published falla despues de `send_message`, SQS puede duplicar mensajes.
Workers downstream deben ser idempotentes.

### TTL Del Item Outbox

`outbox_item`/`outbox_put_transact_item` (`shared/domain/events/outbox.py`) ponen TTL
de 30 dias por defecto (`_OUTBOX_TTL_SECONDS`). Eventos cuyo payload incluya datos
sensibles en texto plano (ej. `OnboardingOtpRequestedEvent.otp`) deben registrarse en
`_SHORT_TTL_EVENT_TYPES` con un TTL acotado (1 hora) para minimizar la ventana de
exposicion en DynamoDB una vez publicados a SQS. Agregar ahi cualquier evento nuevo que
transporte secretos/PII sensible de corta vida.

Los eventos de documentos al comprador (`DocumentBuyerNotificationRequestedEvent`) no
incluyen adjuntos ni datos tributarios completos en el payload. El worker rehidrata el
documento desde DynamoDB, lee XML/RIDE desde S3 y usa locks idempotentes
(`begin_buyer_notification` + `mark_buyer_notification_status`) para evitar duplicar
correos ante reintentos SQS.

### Workers programados (EventBridge)

Para tareas periodicas sin trigger de outbox/SQS, usar una regla EventBridge
(`aws_events.Rule` + `aws_events.Schedule.expression("cron(...)")` +
`aws_events_targets.LambdaFunction(fn)`) apuntando directo a la Lambda, mismo patron de
bundling (`_code`) y permisos IAM explicitos que el resto de Lambdas en `api_stack.py`.

- `certificate_expiry_notifier`: cron diario `cron(0 9 * * ? *)` (09:00 UTC), alerta
  60/30 dias antes de `cert_expires_at`. Ver `CERTIFICATES.md`.
- `subscription_renewal_notifier`: cron diario `cron(0 10 * * ? *)` (10:00 UTC), notifica
  vencimiento, cobra automaticamente si hay `dlocal_payer_id`, gestiona grace period
  `payment_failed`. Ver `SUBSCRIPTIONS.md`.
- `pending_activation_reconciler`: rate `rate(5 minutes)`, activa tenants con
  `pending_payment + pending_order_id` que el flujo principal no pudo completar. Ver `SUBSCRIPTIONS.md`.

Idempotencia entre corridas: si la tarea no tiene una tabla de tracking propia, guardar
el estado "ya procesado" en la entidad de dominio afectada (ver
`cert_expiry_alert_60_sent_at`/`cert_expiry_alert_30_sent_at` en `Tenant`) en vez de
crear una tabla nueva solo para deduplicacion.

## Migraciones

- Schema/tablas/GSIs: CDK.
- Datos/seeds/backfills: `backend/migrations/versions/`.
- Registrar en `backend/migrations/registry.py`.
- Cada migracion debe ser idempotente.
- Si una migracion ya esta `SUCCESS`, crear una correctiva nueva; no modificar la existente.
- `MIGRATIONS_TABLE` trackea `IN_PROGRESS`, `SUCCESS`, `FAILED`.
- `lock_expires_at` permite reintentos si una migracion queda colgada.

## Como Agregar Un Feature Backend

**Paso 0 — Leer antes de escribir codigo:**

- `CLAUDE.md` — reglas no negociables (seguridad, git, validaciones).
- `BACKEND.md` (este archivo) — patrones de construccion.
- El archivo de dominio del feature si ya existe (ej. `INVOICES.md`).
- Los archivos de los dominios que el feature toca. Cada domain file lista sus
  dependencias en la seccion "Lee Tambien". Si el archivo no existe aun, crearlo
  en `context/` antes de empezar, con la seccion "Lee Tambien" como primer paso.

**Pasos de implementacion:**

1. Crear estructura `handler.py`, `schemas.py`, `domain/`, `use_cases/`, `infra/`.
2. Definir comandos en `domain/commands.py`.
3. Definir interfaz ABC en `domain/repositories/`.
4. Poner invariantes en entidad o value objects, no en UI.
5. Handler parsea DTO y construye command.
6. Use case orquesta y retorna entidad/eventos.
7. Repositorio implementa persistencia y `commit(...)` si hay mutacion.
8. Mutaciones HTTP llevan `@idempotent`.
9. Agregar tests de use case y handler con fakes.
10. Actualizar CDK, Postman y el archivo de dominio si cambia contrato o regla.

No copiar plantillas antiguas si no encajan. Mirar `tenants`, `plans` o `clients` y
seguir el patron mas cercano.

## Calidad Esperada

- Preferir reglas de negocio en dominio/use case.
- Preferir constantes nombradas antes que literales repetidos.
- Evitar acoplar Lambdas entre si; usar puertos/adapters o acceso directo controlado.
- Mantener compatibilidad con datos legacy cuando ya existe nota de compatibilidad.
- No hacer refactors grandes sin necesidad; extraer solo cuando elimina duplicacion real.
- Tests deben cubrir reglas nuevas y bugs corregidos.

## Deuda Solventada

- 2026-06-14: se retiro la composicion de items DynamoDB del handler de onboarding; ahora
  vive en `DynamoOnboardingCommitRepository`.
- 2026-06-14: los fallos condicionales de items externos en transacciones DynamoDB se
  distinguen con `ExtraTransactionConditionFailedError`, permitiendo mapear OTP consumido a
  error de negocio sin acoplar `tenants` al dominio onboarding.
- 2026-06-14: `certificate_secret_arn` queda como dato interno de dominio/persistencia y no
  sale en respuestas API.
- 2026-06-14: se elimino el ignore `B904` de Ruff y se encadenaron las excepciones
  (`raise ... from exc`) en `backend/lambdas` y `backend/shared`.
- 2026-06-14: se eliminaron los ignores `S105/S106/S107` de Ruff; la auditoria sin
  excepciones pasa limpia en `backend/lambdas` y `backend/shared`.
- 2026-06-14: `DynamoTenantRepository.commit_admin_events()` ahora incluye
  `ConditionCheck` transaccional de existencia/version/deleted antes de encolar eventos
  administrativos sin mutar la entidad.
- 2026-06-18: bug real detectado en `dev` (500 al emitir documento, `AccessDeniedException`
  en `dynamodb:UpdateItem`): el grant IAM de `documents_fn` sobre la tabla `sequences`
  (Sprint 3) era `grant_read_data`, pero `reserve_next()` hace `UpdateItem` (ADD atómico).
  Corregido a `grant_write_data` en `infra/stacks/api_stack.py` (es write-only: nunca lee
  la tabla `sequences` directamente).
