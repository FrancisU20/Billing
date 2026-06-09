# CodeLabs Billing Cloud

Guia operativa para continuar el proyecto sin re-descubrir contexto.

Ultima actualizacion: 2026-06-09.

## Objetivo Del Producto

SaaS ecuatoriano de facturacion electronica multitenant.

El sistema administra:

- `tenants`: empresas que contrataron el SaaS.
- `plans`: catalogo comercial y limites del SaaS.
- `clients`: compradores/clientes dentro de cada tenant.
- `auth`: login Cognito SRP expuesto por Lambda.
- `workers`: onboarding, emails, migraciones y outbox async.

No existe todavia un Lambda `invoices`. Cuando se implemente, debe respetar las reglas SRI y no mezclar "Consumidor Final" con `clients`.

Cuenta GitHub: `FrancisU20`.
AWS profile del proyecto: `codelabs`.
Region principal: `sa-east-1`.

## Estado Actual

El backend y frontend actuales estan alineados para:

- CRUD y filtros server-side de `tenants`, `plans` y `clients`.
- Estados de tenant: `active`, `suspended`, `inactive`.
- Reactivacion de tenants `inactive` por superadmin.
- `plan_status` calculado en lectura, no persistido.
- Paginacion con `next_token` opaco.
- Mutaciones HTTP con `X-Idempotency-Key`.
- Locks transaccionales para RUC de tenant, slug de plan e identificacion de cliente.
- Outbox transaccional para side effects.

Pendiente funcional natural: dashboard superadmin con estadisticas agregadas. No debe construirse leyendo y sumando listas del frontend; necesita endpoint agregado backend.

## Stack

| Capa | Tecnologia |
| --- | --- |
| Backend | Python 3.12, Lambda ARM64 |
| API | HTTP API Gateway + JWT authorizer Cognito |
| Auth | Amazon Cognito, SRP ejecutado por Lambda |
| DB | DynamoDB on-demand, multi-table |
| Async | SQS + DynamoDB Streams + Outbox |
| Infra | AWS CDK Python |
| Frontend | Expo Router v56, React Native 0.85, React 19 |
| Tests backend | `unittest` + fakes, sin AWS real |
| Tests frontend | Vitest + TypeScript + ESLint |

## Comandos De Validacion

Ejecutar desde la raiz salvo que se indique otra cosa.

```bash
make test
backend/.venv/bin/ruff check backend/lambdas backend/shared backend/tests
cd frontend && npm run typecheck
cd frontend && npm run lint
cd frontend && npm run format:check
cd frontend && npm run test:run
cd frontend && npm run build:web
```

Comandos utiles:

```bash
make superadmin   # sincroniza superadmin Cognito desde variables de entorno o .env
make token        # imprime ID token Cognito por defecto
```

Nunca imprimir tokens, passwords ni secretos en logs compartidos, PRs o documentacion. Para validar token sin exponerlo:

```bash
TOKEN=$(make -s token); echo ${#TOKEN}
```

## Reglas De Git Y Deploy

- No hacer `git push` sin confirmacion explicita.
- No agregar `Co-Authored-By` en commits.
- El deploy normal es por GitHub Actions.
- `cdk deploy` local solo si el usuario lo pide explicitamente.
- Docs-only en raiz (`*.md`), `docs/**` y `postman/**` no deberian disparar deploy pesado.
- Ojo: por el workflow actual, cambios bajo `frontend/**` se clasifican como frontend aunque sean `.md`.

Workflows:

- `develop` -> dev.
- `release/**` o dispatch manual -> staging.
- `master` con `workflow_dispatch` protegido -> prod.

## Estructura Real Del Monorepo

```text
backend/
  lambdas/
    _base/       # framework Lambda: handler, parser, response, permissions, idempotency
    auth/        # rutas publicas de login/refresh/logout/challenge
    tenants/     # empresas SaaS globales
    plans/       # catalogo comercial global
    clients/     # clientes por tenant
    workers/     # outbox_relay, tenant_onboarding, email_notifications, migrations
  shared/        # errores, logging, fechas, db, value objects, audit, secrets, events
  migrations/    # migraciones DynamoDB versionadas
  tests/         # unittest + fakes

frontend/
  app/           # Expo Router: rutas por archivos
  components/    # UI compartida
  constants/     # rutas, tokens, roles
  features/      # auth, tenants, plans, clients, navigation
  lib/           # api client, hooks, theme, utils

infra/
  stacks/        # CDK stacks
  config/        # dev, staging, prod
```

`frontend/CLAUDE.md` apunta a `AGENTS.md`. Para frontend, respetar tambien esa instruccion: Expo cambio; consultar docs versionadas de Expo v56 cuando algo dependa de comportamiento de framework.

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
- Repositorios concretos manejan persistencia, optimistic locking, auditoria, idempotencia y outbox cuando aplique.
- Mutaciones con side effects deben cerrar todo en una sola transaccion DynamoDB: entidad + audit + idempotency completed + outbox.

`_base`:

| Archivo | Uso |
| --- | --- |
| `handler.py` | `@lambda_handler`, errores centralizados, logger |
| `sqs_handler.py` | workers SQS con partial batch failure |
| `parser.py` | `Request.from_event`, `parse`, path params |
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
| `audit/writer.py` | items de auditoria con TTL legal |
| `domain/value_objects` | RUC, email, identificacion Ecuador |
| `domain/events` | DomainEvent, outbox, publisher |

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
{ "success": true, "data": { "items": [], "next_token": "eyJ...", "has_more": true }, "error": null, "meta": {} }
```

Reglas:

- `next_token` es opaco. El frontend no lo decodifica.
- Los filtros via query params deben validarse en handler y aplicarse en repositorio.
- Si se agregan listas nuevas, usar `DEFAULT_LIST_LIMIT` y `clamp_list_limit()` en backend.
- En frontend, usar constante de page size por feature, no literales sueltos.

## Auth

`backend/lambdas/auth/` expone rutas publicas:

| Metodo | Ruta | Body |
| --- | --- | --- |
| POST | `/auth/login` | `{ "username": "...", "password": "..." }` |
| POST | `/auth/refresh` | `{ "refresh_token": "..." }` |
| POST | `/auth/logout` | `{ "access_token": "..." }` |
| POST | `/auth/challenge` | `{ "session": "...", "challenge_name": "...", "responses": {...} }` |

Reglas:

- El frontend nunca llama Cognito directo.
- SRP se ejecuta en backend (`auth/infra/srp.py`).
- Bearer token esperado para rutas protegidas: ID token, porque contiene `custom:tenant_id`, `custom:role`, `custom:is_superadmin`.
- Nunca devolver secretos de challenge SRP: `SALT`, `SRP_B`, `SECRET_BLOCK`.
- `logout` es best-effort ante token ya invalido.

Roles:

| Rol | Acceso |
| --- | --- |
| `superadmin` | global; gestiona tenants y plans |
| `owner` | acceso total dentro del tenant |
| `admin` | gestion dentro del tenant |
| `viewer` | solo lectura dentro del tenant |

## Reglas De Negocio Vigentes

### Tenants

- `Tenant` es global, no tenant-scoped.
- RUC legal no se recicla por soft delete ni por inactivacion.
- `Tenant.status` puede ser:
  - `active`: puede operar.
  - `suspended`: bloqueo temporal reversible.
  - `inactive`: no opera, pero puede reactivarse por superadmin.
- Transiciones permitidas actuales:
  - `active -> suspended`
  - `active -> inactive`
  - `suspended -> active`
  - `suspended -> inactive`
  - `inactive -> active`
  - permanecer en el mismo estado es valido.
- `inactive -> suspended` no es valido. Primero reactivar.
- La regla vive en `Tenant.change_status()`, no solo en UI.
- La UI no debe decir "definitivo" ni "irreversible" si el estado puede reactivarse.
- `DELETE /tenants/{id}` existe como soft delete backend, pero no esta expuesto en UI porque una empresa conserva comprobantes/datos auditables.

### Plans

- `Plan.id` es UUID e identidad interna.
- `Plan.slug` es identidad publica e inmutable despues de crear.
- Slug unico con lock transaccional `PLAN_SLUG#{slug}`.
- Precios se modelan como `Decimal` y se serializan como string.
- `document_limit = -1` significa ilimitado.
- `limit_cycle` actual: `month` o `year`.
- `GET /plans` es publico para pricing.
- Mutaciones de plans requieren superadmin e idempotencia.

### Plan Status

- No existe "trial" como estado.
- `plan_status` no se persiste.
- Se calcula en `Tenant.effective_plan_status(now)` usando `plan_cycle_ends_at`.
- Valores actuales: `active`, `expired`.
- Si luego se agregan facturas/emisiones, el agotamiento de `document_limit` debe incorporarse al calculo real, no a un campo persistido que pueda desincronizarse.

### Clients

- `Client` pertenece a un tenant.
- `Consumidor Final` no es `Client`.
- Para invoices, consumidor final deberia emitirse como modo tributario:
  - `tipoIdentificacionComprador = 07`
  - `identificacionComprador = 9999999999999`
  - `client_id = null`
- Identificaciones soportadas: RUC, cedula, pasaporte, exterior.
- La identificacion es unica por tenant con lock transaccional `CLIENT_IDENTIFICATION#{identification}`.
- A diferencia del RUC de tenant, el lock de cliente se libera en soft delete para permitir reutilizacion dentro del tenant.
- Busqueda exacta por identificacion usa GSI `identification-index`.
- Busqueda `q` es v1 simple: camina paginas DynamoDB hasta llenar `limit` o agotar resultados.

## DynamoDB

### Tenants Table

`tenants` usa `id` como PK.

```text
Tenant:
  id = "{uuid}"
  entity_type = "TENANT"
  ruc = "179..."

RUC lock:
  id = "RUC#179..."
  entity_type = "TENANT_RUC_LOCK"
  tenant_id = "{uuid}"
```

`ruc-index` sirve para lookup, no para unicidad. La unicidad real es el lock en `TransactWriteItems`.

### Plans Table

```text
Plan:
  id = "{uuid}"
  entity_type = "PLAN"
  slug = "basic"

Slug lock:
  id = "PLAN_SLUG#basic"
  entity_type = "PLAN_SLUG_LOCK"
  plan_id = "{uuid}"
```

Compatibilidad: pueden existir planes legacy sin `entity_type = PLAN` o sin lock. Los repositorios deben tratarlos como planes validos y las migraciones deben consultar por slug antes de crear.

### Tenant-Scoped Tables

Convencion de `BaseRepository`:

```text
PK = "TENANT#{tenant_id}"
SK = "{PREFIX}#{entity_id}"
```

Ejemplo clients:

```text
pk = "TENANT#t-123"
sk = "CLIENT#c-456"
```

### Paginacion

- DynamoDB aplica `Limit` antes de `FilterExpression`; para filtros in-memory (`q`, `plan_status`) el repositorio puede necesitar caminar varias paginas.
- Backend: usar `shared/db/limits.py`.
- Frontend: `usePaginatedList()` evita doble `fetchMore` y no debe llamarse mientras `loading` o `loadingMore` estan activos.

## Idempotencia HTTP

Toda mutacion HTTP debe usar `@idempotent` y exigir `X-Idempotency-Key`.

La key queda ligada a:

- tenant/global scope
- method
- path
- hash canonico del body

Estados:

- `IN_PROGRESS`
- `COMPLETED`
- `FAILED`

Si un request igual ya completo, se devuelve respuesta cacheada.
Si la misma key se reutiliza con otro body/path/method, responder `IDEMPOTENCY_KEY_REUSED`.

Para mutaciones con repositorio transaccional, el `COMPLETED` se escribe en el mismo `TransactWriteItems` que el cambio de negocio.

## Outbox Y Workers

Side effects no se ejecutan antes de confirmar la mutacion principal.

Flujo:

```text
HTTP handler -> use case -> repo.commit()
repo.commit() -> DynamoDB transaction: entity + audit + idempotency + outbox
OutboxRelayWorker -> SQS
Worker consumidor -> side effect idempotente
```

Workers actuales:

- `tenant_onboarding`: crea/sincroniza usuario Cognito.
- `email_notifications`: envia email Brevo de bienvenida.
- `outbox_relay`: publica eventos outbox a SQS.
- `migrations`: ejecuta migraciones de datos.

Regla importante: si outbox marca published falla despues de `send_message`, SQS puede duplicar mensajes. Workers downstream deben ser idempotentes.

## Migraciones

- Schema/tablas/GSIs: CDK.
- Datos/seeds/backfills: `backend/migrations/versions/`.
- Registrar migraciones en `backend/migrations/registry.py`.
- Cada migracion debe ser idempotente.
- Si una migracion ya esta `SUCCESS`, no se modifica para "correr otra vez"; crear una migracion correctiva nueva.
- `MIGRATIONS_TABLE` trackea `IN_PROGRESS`, `SUCCESS`, `FAILED`.
- `lock_expires_at` permite reintentos si una migracion queda colgada.

## Frontend

Arquitectura:

```text
app/                  # rutas Expo Router
features/{area}/api.ts
features/{area}/schemas.ts
features/{area}/types.ts
features/{area}/hooks/
features/{area}/components/
features/{area}/screens/
components/ui/        # primitivas compartidas
lib/api/              # client y errores
lib/hooks/            # hooks reutilizables
```

Reglas:

- Validar respuestas con Zod en `api.ts`.
- Mantener `types.ts` derivados de `schemas.ts` cuando aplique.
- No duplicar hooks de fetch/paginacion si `usePaginatedList` cubre el caso.
- No duplicar acciones/metadatos de filas; usar `ListItemAction` y `ListItemMeta`.
- Para filtros, separar draft UI de filtros aplicados:
  - `draft`: estado editable.
  - `filters`: objeto que dispara request al presionar aplicar.
- Evitar objetos inline como filtros permanentes si un hook depende de ellos. Usar constantes estables, como `ACTIVE_PLANS_FILTER`.
- Las metricas en listados actuales cuentan items cargados, no totales reales. Para dashboards usar endpoint agregado backend.

Comandos frontend:

```bash
cd frontend
npm run format:check
npm run typecheck
npm run lint
npm run test:run
npm run build:web
```

Nota Expo: `expo-env.d.ts` esta gitignored; CI puede no cargar augmentations de `expo/types`. Cuando se componga `Pressable` con callback style, pasar `state` completo o asumir solo `{ pressed: boolean }`.

## Seguridad

Reglas no negociables:

1. `tenant_id` siempre viene del JWT; nunca del body.
2. Repositorios tenant-scoped reciben `tenant_id` obligatorio en constructor.
3. Soft delete salvo locks legales/transaccionales que se conservan.
4. Nunca devolver stacktrace al cliente.
5. Secretos en Secrets Manager o `.env` privado; nunca hardcodeados.
6. No loguear passwords temporales, tokens, API keys ni HTML con secretos.
7. Mensajes HTTP de errores de negocio vienen de `AppError.default_message`.
8. Mutaciones con side effects usan outbox transaccional.
9. `Tenant.plan_id` se valida contra plan existente y activo antes de crear tenant.
10. Dinero con `Decimal`; API/DynamoDB string decimal exacto.

## Secretos

`.env` y `.env.*` son privados e ignorados por Git.
Los scripts `make superadmin` y `make token` leen variables del entorno y, si existe, del `.env` de la raiz.

Variables relevantes para superadmin/token:

```text
SUPERADMIN_EMAIL=...
SUPERADMIN_PASSWORD=...
COGNITO_USER_POOL_ID=...
COGNITO_WEB_CLIENT_ID=...
```

`make superadmin` es idempotente: crea o actualiza usuario superadmin Cognito.
`make token` usa `USER_SRP_AUTH` y por defecto imprime `IdToken`.

## Como Agregar Un Feature Backend

Checklist:

1. Crear estructura `handler.py`, `schemas.py`, `domain/`, `use_cases/`, `infra/`.
2. Definir comandos en `domain/commands.py`.
3. Definir interfaz ABC en `domain/repositories/`.
4. Poner invariantes en entidad o value objects, no en UI.
5. Handler parsea DTO y construye command.
6. Use case orquesta y retorna entidad/eventos.
7. Repositorio implementa persistencia y `commit(...)` si hay mutacion.
8. Mutaciones HTTP llevan `@idempotent`.
9. Agregar tests de use case y handler con fakes.
10. Actualizar CDK, Postman y este documento si cambia contrato o regla de negocio.

No copiar plantillas antiguas si no encajan. Mirar primero `tenants`, `plans` o `clients` y seguir el patron mas cercano.

## Como Agregar Un Feature Frontend

Checklist:

1. Definir Zod schemas en `features/{area}/schemas.ts`.
2. Exportar tipos desde `types.ts`.
3. Implementar `api.ts` con validacion de respuesta.
4. Usar hooks existentes (`useAsync`, `usePaginatedList`) antes de crear uno nuevo.
5. Crear componentes pequenos y reutilizables cuando haya duplicacion real.
6. Mantener pantallas como composicion de componentes, no como archivo monolitico si crecen.
7. Correr `typecheck`, `lint` y tests.

## Calidad Esperada

- Preferir reglas de negocio en dominio/use case.
- Preferir constantes nombradas antes que literales repetidos.
- Evitar acoplar Lambdas entre si; usar puertos/adapters o acceso directo controlado si aplica.
- Mantener compatibilidad con datos legacy cuando ya existe nota de compatibilidad.
- No hacer refactors grandes sin necesidad; extraer solo cuando elimina duplicacion real o reduce riesgo.
- Tests deben cubrir reglas nuevas y bugs corregidos.

## Dashboard Superadmin - Siguiente Feature Probable

Si se implementa:

- Crear endpoint backend agregado para superadmin, por ejemplo `GET /superadmin/dashboard` o ruta equivalente.
- No calcular estadisticas recorriendo listas paginadas desde frontend.
- Metricas esperadas:
  - tenants totales por estado.
  - planes activos/inactivos.
  - tenants por plan.
  - ingresos estimados por precio de plan y tenants activos.
  - clientes totales si se puede agregar sin scan caro por tenant; si no, documentar limite v1.
- Definir claramente si "planes vendidos" significa tenants activos por `plan_id`, no planes catalogo.
- Agregar tests backend de permisos superadmin y calculos.

## Auditorias Recientes Vigentes

2026-06-09 (v2):

- `GET /plans` y `GET /plans/{slug}` son publicos y ahora siempre filtran `active=true`. Cualquier `status` que pase un caller publico se ignora y se sobreescribe con `"active"`. Planes inactivos devuelven 404 en `GET /plans/{slug}`.
- `plans` lista con scan completo sin paginacion en `plan_repository.py:list()`. Aceptable para catalogo (volumen < 100 planes). No replicar este patron para dashboard ni endpoints de alta cardinalidad.
- `tenants` lista con scan paginado y `FilterExpression` en `tenant_repository.py:list()`. Aceptable para listado admin. Para dashboard superadmin diseñar endpoints agregados dedicados, no calcular sumando scans.

2026-06-09:

- `inactive` ya no es irreversible en UI.
- Regla de transicion de tenant vive en dominio.
- `usePaginatedList` centraliza paginacion frontend y evita doble `fetchMore`.
- `ListItemMeta` y `ListItemAction` eliminan duplicacion en filas de clients/tenants/plans.
- Constantes de paginacion frontend/backend reemplazan literales sueltos.

2026-06-08:

- `plan_status` calculado, sin trial.
- Filtros server-side alineados para plans, tenants y clients.
- `parse_date_boundary` vive en `shared/dates.py`.
- `clients` implementado completo con lock transaccional de identificacion.

2026-06-07:

- Auth Lambda SRP completo.
- Runner de migraciones.
- FrontendStack S3 + CloudFront.
- Fix de doble serializacion DynamoDB en `transact_write_items`: usar Python dicts puros con `resource.meta.client`.

## Antes De Cerrar Cualquier Cambio

1. Revisar `git status --short`.
2. No revertir cambios ajenos.
3. Correr validaciones relevantes.
4. Si tocaste backend: `make test` y ruff.
5. Si tocaste frontend: `format:check`, `typecheck`, `lint`, `test:run`; si cambia build/routing, tambien `build:web`.
6. Reportar lo que cambiaste, pruebas ejecutadas y cualquier riesgo residual.
