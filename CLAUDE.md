# CodeLabs Billing Cloud

## Contexto

SaaS ecuatoriano de facturación electrónica multitenant.
Cuenta GitHub: `FrancisU20` · AWS perfil: `codelabs` · Región: `sa-east-1`

## Stack principal

| Capa | Tecnología |
|---|---|
| Runtime | Python 3.12 · ARM64 (Graviton2) |
| Base de datos | DynamoDB on-demand (multi-table) |
| Auth | Amazon Cognito · SRP · consumido via Lambda |
| API | HTTP API Gateway · JWT authorizer nativo (Cognito) |
| Storage | S3 (certificados firma electrónica) |
| Queues | SQS (procesamiento async) |
| Infra | AWS CDK Python |
| Frontend | Expo Router (web + iOS + Android — mismo código) |
| Local | Servidor uvicorn que simula API Gateway + Cognito |

**Costo dev estimado: < $2/mes** (DynamoDB free tier, Lambda free tier, sin VPC)

---

## CI/CD y despliegues

El despliegue normal se hace por GitHub Actions, no con `cdk deploy` local:

- `develop` → workflow `Deploy — Dev` → ambiente `dev`.
- `release/**` o dispatch manual → workflow `Deploy — Staging` → ambiente `staging`.
- `master` solo con `workflow_dispatch` y protección de environment → `prod`.

`Deploy — Dev` es selectivo por paths:

- Cambios docs-only (`CLAUDE.md`, `*.md`, `docs/**`, `postman/**`) corren solo
  detección + summary; no ejecutan CI pesada ni deploy AWS.
- Cambios en `backend/**` o `infra/**` ejecutan CI/CD y despliegue API según aplique.
- Cambios en `backend/migrations/**` también invocan el Lambda de migraciones.
- Cambios en `frontend/**` ejecutan solo el deploy frontend.
- Cambios en `.github/workflows/**`, `.github/actions/**` o rutas desconocidas se
  tratan conservadoramente como deployables.

Uso local permitido:

- `cdk synth` / `cdk diff` para validar infraestructura antes de abrir PR.
- `cdk deploy` local solo si se pide explícitamente como excepción operativa.

Reglas:

- No hacer `git push` sin confirmación explícita.
- No agregar `Co-Authored-By` en commits.
- Perfil AWS del proyecto: `codelabs`; región: `sa-east-1`.

---

## Monorepo

```
backend/
  lambdas/
    _base/       ← framework Lambda — NO contiene lógica de negocio
    auth/        ← Lambda HTTP: login, refresh, logout (Cognito SRP)
    tenants/     ← Lambda HTTP: CRUD empresas
    clients/     ← Lambda HTTP: CRUD clientes (compartidos entre tenants)
    invoices/    ← Lambda HTTP: emisión de comprobantes SRI
    workers/     ← Lambdas SQS: procesamiento async
  shared/        ← utilidades compartidas entre todos los Lambdas
  migrations/    ← migraciones de datos DynamoDB
  tests/         ← unit tests con unittest + fakes, sin AWS real

frontend/
  app/           ← Expo Router (rutas = archivos)
  components/
  lib/

infra/
  stacks/        ← CDK stacks por dominio funcional
  config/        ← dev.yaml, staging.yaml, prod.yaml

local/
  server.py      ← uvicorn que simula API Gateway + inyecta JWT claims
  authorizer.py  ← valida tokens JWT en local
  Makefile
```

---

## Auth Lambda — Cognito SRP

`backend/lambdas/auth/` expone las rutas públicas que generan o renuevan JWT. No usan
JWT authorizer porque son el punto de entrada para obtener tokens.

| Método | Ruta | Body | Respuesta |
|---|---|---|---|
| POST | `/auth/login` | `{ "username": "...", "password": "..." }` | Tokens Cognito o challenge pendiente |
| POST | `/auth/refresh` | `{ "refresh_token": "..." }` | Nuevo `id_token` y `access_token` |
| POST | `/auth/logout` | `{ "access_token": "..." }` | `204` y cierre global en Cognito |
| POST | `/auth/challenge` | `{ "session": "...", "challenge_name": "...", "responses": {...} }` | Tokens o siguiente challenge |

Reglas específicas:

- Login usa `USER_SRP_AUTH` completo en Python puro dentro del Lambda. El frontend
  nunca llama Cognito directamente y nunca calcula SRP.
- El token que se usa como Bearer en rutas protegidas es el **ID token**, porque
  contiene `custom:tenant_id`, `custom:role` y `custom:is_superadmin`.
- `/auth/challenge` debe soportar `NEW_PASSWORD_REQUIRED` y futuros challenges de
  Cognito sin agregar rutas nuevas.
- Nunca devolver al cliente parámetros secretos del challenge SRP: `SALT`, `SRP_B`
  ni `SECRET_BLOCK`.
- Validar que Cognito devuelva `IdToken`, `AccessToken`, `ExpiresIn` y `TokenType`
  antes de responder `200`.
- Las pruebas unitarias de auth viven en `backend/tests/unit/lambdas/auth/` y deben
  cubrir handler, provider Cognito, mapeo de errores Cognito y sanitización de
  challenges.
- La colección Postman en `postman/CodeLabsBillingCloud.postman_collection.json`
  tiene una carpeta `Auth` que guarda `id_token` como `{{token}}`.

---

## Cómo crear un nuevo Lambda — guía paso a paso

### 1. Estructura obligatoria de carpetas

```
lambdas/nuevo-feature/
  handler.py              ← PRESENTACIÓN: entry point AWS + composición DI
  schemas.py              ← DTOs Pydantic (validación HTTP — no dominio)
  domain/
    entity.py             ← Entidad pura (hereda BaseEntity)
    commands.py           ← CreateXCommand, UpdateXCommand (dataclasses)
    events.py             ← XCreatedEvent (hereda DomainEvent)
    errors.py             ← XNotFoundError, XConflictError (con code y default_message)
    repositories/
      i_x_repository.py   ← Interfaz ABC — el dominio NO conoce DynamoDB
  use_cases/
    create_x.py           ← 1 archivo por caso de uso
    get_x.py
    list_x.py
    update_x.py
    delete_x.py
  infra/
    x_repository.py       ← Implementación DynamoDB (extiende BaseRepository)
```

### 2. handler.py — plantilla

```python
from lambdas._base.handler import lambda_handler
from lambdas._base.idempotency import idempotent, require_current_context
from lambdas._base.parser import Request, parse
from lambdas._base.permissions import require_role
from lambdas._base.response import ApiResponse
from lambdas.nuevo_feature.domain.commands import CreateXCommand
from lambdas.nuevo_feature.infra.x_repository import DynamoXRepository
from lambdas.nuevo_feature.schemas import CreateXRequest
from lambdas.nuevo_feature.use_cases.create_x import CreateXUseCase
from shared.config import env
from shared.db.client import get_table

# ── Inicialización cold start — fuera del handler ─────────────────────────────
_table       = get_table("X_TABLE")
_audit_table = get_table("AUDIT_LOG_TABLE") if env("AUDIT_LOG_TABLE", "") else None
_outbox_table = get_table("OUTBOX_TABLE") if env("OUTBOX_TABLE", "") else None


def _repo(request: Request) -> DynamoXRepository:
    return DynamoXRepository(request.tenant_id, _table, _audit_table, _outbox_table)

# ── Handlers ──────────────────────────────────────────────────────────────────

@lambda_handler
@require_role("owner", "admin")
@idempotent
def create(request: Request, context) -> dict:
    body    = parse(CreateXRequest, request.body)
    command = CreateXCommand(
        nombre     = body.nombre,
        created_by = request.user_id,
    )
    repo     = _repo(request)
    use_case = CreateXUseCase(repo)
    result, events = use_case.execute(command)
    response = ApiResponse.created(result.to_dict(), request.request_id)
    repo.commit(
        entity      = result,
        user_id     = request.user_id,
        action      = "CREATE",
        events      = events,
        idempotency = require_current_context(),
        response    = response,
    )
    return response


# Lambda entry point — API Gateway llama a este handler
def handler(event: dict, context) -> dict:
    method = event.get("requestContext", {}).get("http", {}).get("method", "")
    path   = event.get("rawPath", "")

    # Enrutar por método + path
    if method == "POST":
        return create(event, context)
    # ...más rutas

    from shared.errors import NotFoundError
    from lambdas._base.response import ApiResponse
    return ApiResponse.error(NotFoundError(), event.get("requestContext", {}).get("requestId", ""))
```

### 3. domain/errors.py — plantilla

```python
from shared.errors import NotFoundError, ConflictError, BusinessError

class XNotFoundError(NotFoundError):
    code            = "X_NOT_FOUND"
    default_message = "El recurso X no fue encontrado."

class XAlreadyExistsError(ConflictError):
    code            = "X_ALREADY_EXISTS"
    default_message = "Ya existe un X con esos datos."
```

### 4. domain/repositories/i_x_repository.py — plantilla

```python
from abc import ABC, abstractmethod
from lambdas.nuevo_feature.domain.entity import X

class IXRepository(ABC):
    @abstractmethod
    def get_by_id(self, id: str) -> X: ...

    @abstractmethod
    def save(self, x: X) -> None: ...

    @abstractmethod
    def list(self, limit: int, next_token: str | None) -> tuple[list[X], str | None]: ...

    @abstractmethod
    def delete(self, id: str, deleted_by: str) -> None: ...
```

### 5. use_cases/create_x.py — plantilla

```python
from dataclasses import dataclass
from lambdas.nuevo_feature.domain.entity import X
from lambdas.nuevo_feature.domain.events import XCreatedEvent
from lambdas.nuevo_feature.domain.repositories.i_x_repository import IXRepository
from shared.domain.events.domain_event import DomainEvent

@dataclass
class CreateXCommand:
    nombre:     str
    created_by: str

class CreateXUseCase:
    def __init__(self, repo: IXRepository) -> None:
        self._repo = repo   # DI por constructor — testeable sin DynamoDB

    def execute(self, cmd: CreateXCommand) -> tuple[X, list[DomainEvent]]:
        x = X.create(cmd)          # lógica en la entidad
        return x, [XCreatedEvent(x_id=x.id, tenant_id=x.tenant_id)]
```

### 6. infra/x_repository.py — plantilla

```python
from boto3.dynamodb.conditions import Attr
from shared.db.base_repository import BaseRepository
from lambdas.nuevo_feature.domain.entity import X
from lambdas.nuevo_feature.domain.errors import XNotFoundError
from lambdas.nuevo_feature.domain.repositories.i_x_repository import IXRepository

class DynamoXRepository(BaseRepository, IXRepository):
    _prefix = "X"

    def get_by_id(self, id: str) -> X:
        item = self._get_raw(id)
        if not item:
            raise XNotFoundError()
        return self._from_item(item)

    def save(self, x: X) -> None:
        item = self._to_item(x)
        old  = self._get_raw(x.id)
        # Optimistic locking con objetos Attr de boto3 (no strings)
        condition = Attr("pk").not_exists() | Attr("version").eq(x.version - 1)
        self._put_raw(item, condition=condition)
        self._audit("SAVE", x.id, x.updated_by, old, item)

    def list(self, limit: int = 20, next_token: str | None = None):
        items, cursor = self._list_raw(limit=limit, next_token=next_token)
        return [self._from_item(i) for i in items], cursor

    def delete(self, id: str, deleted_by: str) -> None:
        x = self.get_by_id(id)
        x.soft_delete(deleted_by)
        self.save(x)

    def _to_item(self, x: X) -> dict:
        return {
            "pk":         self._pk(),
            "sk":         self._sk(x.id),
            "id":         x.id,
            "tenant_id":  x.tenant_id,
            "nombre":     x.nombre,
            "version":    x.version,
            "deleted":    x.deleted,
            "created_at": x.created_at.isoformat(),
            "updated_at": x.updated_at.isoformat(),
            "created_by": x.created_by,
            "updated_by": x.updated_by,
        }

    def _from_item(self, item: dict) -> X:
        from datetime import datetime
        return X(
            id         = item["id"],
            tenant_id  = item["tenant_id"],
            nombre     = item["nombre"],
            version    = item["version"],
            deleted    = item.get("deleted", False),
            created_at = datetime.fromisoformat(item["created_at"]),
            updated_at = datetime.fromisoformat(item["updated_at"]),
            created_by = item.get("created_by", ""),
            updated_by = item.get("updated_by", ""),
        )
```

Si el Lambda emite eventos o usa `@idempotent`, el repositorio debe exponer un
`commit(...)` transaccional como `DynamoTenantRepository.commit`: entidad,
auditoría, outbox e idempotencia se escriben juntos. `save()` queda solo como
wrapper para operaciones internas simples sin side effects.

---

## _base — referencia rápida

| Archivo | Qué hace |
|---|---|
| `handler.py` | `@lambda_handler`: parsea event, vincula logger, try/except central |
| `sqs_handler.py` | `@sqs_handler`: itera Records, partial batch failure automático |
| `response.py` | `ApiResponse.ok/created/no_content/paginated/error` |
| `parser.py` | `Request.from_event()` + `parse(Schema, data)` — Pydantic validation |
| `permissions.py` | `@require_role("owner", "admin")` |
| `idempotency.py` | `@idempotent` — previene duplicados con X-Idempotency-Key |

## shared — referencia rápida

| Módulo | Qué hace |
|---|---|
| `errors.py` | Jerarquía AppError — cada error tiene `code` y `default_message` |
| `logger.py` | `get_logger(__name__)` — JSON estructurado con contexto acumulable |
| `config.py` | `env("VAR")` — falla en cold start si var requerida falta. `ENV`, `LOG_LEVEL`, `REGION` globales. Cada Lambda declara solo sus propias vars. |
| `domain/base_entity.py` | `BaseEntity` con id, tenant_id, timestamps, version, soft delete |
| `domain/events/domain_event.py` | `DomainEvent` base — se emite desde use cases |
| `domain/events/outbox.py` | Construye items de outbox para guardar eventos en la misma transacción DynamoDB |
| `domain/events/publisher.py` | Serialización estándar de eventos; publicación directa solo para casos simples/legacy |
| `domain/value_objects/ruc.py` | `RUC("1234567890001")` — valida con algoritmo SRI |
| `domain/value_objects/email.py` | `Email("a@b.com")` — normaliza a minúsculas |
| `db/client.py` | `get_table("TENANTS_TABLE")` — singleton boto3 |
| `db/base_repository.py` | `BaseRepository` — tenant isolation, audit, soft delete |
| `db/paginator.py` | `encode_cursor / decode_cursor` — DynamoDB pagination |
| `secrets/client.py` | `get_secret("nombre")` — cache TTL en memoria |
| `decorators/retry.py` | `@retry(exceptions=(...), max_attempts=3)` |

---

## Seguridad — reglas no negociables

1. `tenant_id` siempre del JWT — **NUNCA del body del request**
2. Todo repositorio recibe `tenant_id` en el constructor — no tiene default
3. Soft delete siempre — **nunca llamar `delete_item` directamente**
4. Stacktrace completo → CloudWatch — **nunca al HTTP response**
5. Secretos en Secrets Manager — **nunca en env vars en texto plano**
6. Los mensajes de error al cliente vienen de `default_message` — **nunca strings hardcodeados en Lambdas**
7. Toda mutación HTTP usa `@idempotent` y exige `X-Idempotency-Key`
8. Eventos de dominio que disparan side effects salen por outbox transaccional — no publicar SQS antes de confirmar DynamoDB
9. `Tenant.plan_id` siempre se valida contra un plan existente y activo antes de crear la empresa
10. Montos de dinero se modelan como `Decimal` y se serializan como string decimal exacto en API/DynamoDB

---

## Roles Cognito

| Rol | Acceso |
|---|---|
| `superadmin` | Global — crea y gestiona tenants, omite verificación de rol |
| `owner` | Dueño del tenant — acceso total dentro de su tenant |
| `admin` | Admin del tenant — todo excepto borrar empresa y billing |
| `viewer` | Solo lectura dentro del tenant |

Claims en el JWT: `custom:tenant_id`, `custom:role`, `custom:is_superadmin`

---

## Respuesta estándar — contrato con el frontend

```json
// Éxito
{ "success": true,  "data": {...},  "error": null,  "meta": {"request_id": "...", "timestamp": "..."} }

// Error
{ "success": false, "data": null, "error": {"code": "TENANT_NOT_FOUND", "message": "La empresa no fue encontrada."}, "meta": {...} }

// Lista paginada
{ "success": true, "data": {"items": [...], "next_token": "eyJ...", "has_more": true}, "error": null, "meta": {...} }
```

---

## Clean Architecture dentro de cada Lambda

```
Event AWS → handler.py [PRESENTACIÓN]
              ↓ Command
           use_cases/ [APLICACIÓN]        ← orquesta, no conoce DynamoDB
              ↓ entidades
           domain/ [DOMINIO]              ← Python puro, zero imports externos
              ↑ implementa ABC
           infra/ [INFRAESTRUCTURA]       ← DynamoDB, boto3, servicios externos
```

El dominio define la interfaz (ABC), la infra la implementa.
El use case depende de la interfaz — nunca de la implementación concreta.

Para mutaciones con side effects, el use case prepara la entidad y los eventos,
pero el commit final vive en infraestructura. Esto permite que el handler
construya la respuesta HTTP y que el repositorio cierre en una sola transacción
DynamoDB: cambio de negocio, auditoría, outbox e idempotencia.

---

## Pruebas unitarias

Runner estándar:

```bash
make test
```

El target usa `unittest` de la librería estándar:

```bash
PYTHONPATH=backend:local backend/.venv/bin/python -m unittest discover -s backend/tests -p 'test_*.py'
```

Convención de carpetas:

```
backend/tests/
  unit/
    support.py                      ← fakes y builders reutilizables
    lambdas/
      _base/                        ← parser, idempotency, handlers base
      tenants/                      ← handler + use cases del Lambda tenants
      workers/                      ← workers SQS/streams
```

Reglas:

1. Unit tests no tocan AWS real, DynamoDB real, SQS real ni Cognito real.
2. Use cases se prueban con fakes de las interfaces del dominio.
3. Handlers se prueban inyectando factories/puertos fake; no se mockean reglas de negocio.
4. Workers se prueban con eventos AWS sintéticos y clientes fake.
5. Los asserts deben verificar comportamiento público: response HTTP, eventos emitidos, commits, llamadas a puertos.
6. No agregar dependencias de test al `backend/requirements.txt`, porque ese archivo se bundlea en Lambda.
7. Si un test necesita variables de entorno, usa valores dummy y explícitos en el test.

Al crear un nuevo Lambda, agregar como mínimo:

- Tests de use cases felices y errores de negocio.
- Tests del handler para permisos, parsing y composición del commit/publicación.
- Tests de workers para éxito, evento ignorado y partial batch failure cuando aplique.

---

## DynamoDB — convención de claves

```
PK = "TENANT#{tenant_id}"
SK = "{PREFIX}#{entity_id}"

Ejemplo tenants:
  PK = "TENANT#t-123"
  SK = "TENANT#t-123"   (el tenant apunta a sí mismo)

Ejemplo clients dentro de un tenant:
  PK = "TENANT#t-123"
  SK = "CLIENT#c-456"
```

Las tablas y GSIs se gestionan en CDK (infra/stacks/).
Las migraciones de datos (seeds, backfills) van en `migrations/versions/`.
No se usa DynamoDB Local; el entorno local apunta a tablas AWS dev gestionadas por CDK.

### Unicidad de RUC en tenants

El RUC es identidad legal y **no se recicla por soft delete**.

La tabla `tenants` usa `id` como PK para el tenant real, y además guarda un
ítem centinela de unicidad:

```
Tenant:
  id = "{uuid}"
  entity_type = "TENANT"
  ruc = "179..."

Lock RUC:
  id = "RUC#179..."
  entity_type = "TENANT_RUC_LOCK"
  tenant_id = "{uuid}"
  locked_ruc = "179..."
```

La creación de tenant debe usar `TransactWriteItems` para insertar ambos ítems
con `attribute_not_exists(id)`. Esto evita duplicados bajo concurrencia real.
El GSI `ruc-index` queda solo para lookup, no como mecanismo de unicidad.
El soft delete **no borra** el lock; una futura reactivación debe ser un flujo
explícito, no una recreación silenciosa.

### Unicidad de slug en plans

El slug de plan es una identidad pública y debe ser único bajo concurrencia.

La tabla `plans` usa `id` como PK para el plan real, y además guarda un ítem
centinela de unicidad:

```
Plan:
  id = "{uuid}"
  entity_type = "PLAN"
  slug = "basic"

Lock slug:
  id = "PLAN_SLUG#basic"
  entity_type = "PLAN_SLUG_LOCK"
  plan_id = "{uuid}"
  locked_slug = "basic"
```

La creación de plan debe usar `TransactWriteItems` para insertar ambos ítems con
`attribute_not_exists(id)`. El GSI `slug-index` queda solo para lookup público,
no como garantía de unicidad. Las actualizaciones de planes usan optimistic
locking con `version`.

Compatibilidad legacy: pueden existir planes creados antes del endurecimiento sin
`entity_type = "PLAN"` ni lock `PLAN_SLUG#{slug}`. `get_by_slug()` debe tratarlos
como planes válidos igual que `list()`, y cualquier migración/backfill de planes
debe consultar por slug antes de crear nuevos registros. Nunca asumir que la
ausencia del lock implica ausencia del plan.

### Idempotencia HTTP

Las operaciones mutantes con `@idempotent` reservan primero la key en DynamoDB:

```
pk = "TENANT#{tenant_id}#{X-Idempotency-Key}"
pk = "GLOBAL#{user_id}#{X-Idempotency-Key}"   # operaciones globales/superadmin
status = IN_PROGRESS | COMPLETED | FAILED
method = "POST"
path = "/tenants"
body_hash = sha256(JSON canonico)
```

La reserva usa `ConditionExpression`, por lo que dos requests concurrentes con
la misma key no ejecutan dos veces el caso de uso. Mientras una operación está
`IN_PROGRESS`, se responde `IDEMPOTENCY_IN_PROGRESS`. Al completar, se cachea la
respuesta por 24h usando TTL.

La key queda ligada a `method + path + body_hash`. Si se reutiliza la misma key
con otro request, se responde `IDEMPOTENCY_KEY_REUSED`. Si el handler falla, la
reserva queda `FAILED` por una ventana corta para permitir reintentos reales.

En operaciones que persisten datos, el cierre `COMPLETED` se agrega al mismo
`TransactWriteItems` que guarda el cambio de negocio, la auditoría y el outbox.
El fallback no transaccional de `idempotency.py` existe solo para mutaciones
simples que no tengan repositorio transaccional.

### Outbox transaccional

Los side effects no deben ejecutarse desde el handler antes de confirmar la
mutación principal. El patrón oficial es:

1. El use case retorna `(entity, events)`.
2. El repositorio hace un solo `TransactWriteItems` con entidad, auditoría,
   `COMPLETED` de idempotencia y registros `PENDING` en `outbox`.
3. `OutboxRelayWorker` lee el stream DynamoDB de `outbox` y publica a SQS.
4. El worker consumidor procesa SQS de forma idempotente.

Estados de outbox: `PENDING`, `PUBLISHED`, `SKIPPED`. Los eventos sin ruta SQS
configurada se marcan `SKIPPED` para no quedar reintentando indefinidamente.
Los items tienen TTL de 30 días.

En local, si `OUTBOX_TABLE` apunta a la tabla AWS dev, los writes locales pueden
disparar el stream/worker desplegado. Dejar `OUTBOX_TABLE` vacío desactiva ese
side effect desde el handler local.

### Secretos y credenciales locales

- Nunca loguear contraseñas temporales ni tokens. CloudWatch no es un canal de entrega de secretos.
- El onboarding de tenants crea el usuario Cognito con email nativo suprimido y entrega la contraseña temporal vía Brevo.
- Si el reintento encuentra un usuario Cognito aún en onboarding (`FORCE_CHANGE_PASSWORD` o `RESET_REQUIRED`), se resetea una nueva contraseña temporal y se reenvía el email. Si el usuario ya completó onboarding, no se reenvía.
- `local/.env` es el único lugar local para credenciales personales y queda ignorado por Git.
- `scripts/create_superadmin.py` no contiene secretos: lee `SUPERADMIN_EMAIL` y `SUPERADMIN_PASSWORD` desde `local/.env`.
- Las plantillas sin secretos, como `local/.env.example`, sí deben versionarse.

### Token local superadmin

`make superadmin` sincroniza el usuario superadmin en Cognito con las variables
de `local/.env`. Es idempotente: si el usuario ya existe, actualiza atributos
y fija la contraseña como permanente.

Variables requeridas en `local/.env`:

```
SUPERADMIN_EMAIL=...
SUPERADMIN_PASSWORD=...
COGNITO_USER_POOL_ID=...
COGNITO_WEB_CLIENT_ID=...
```

`make token` ejecuta login Cognito con `USER_SRP_AUTH` y escribe el token en
stdout. Por defecto imprime el `IdToken`, que es el JWT esperado por el
authorizer HTTP API. Se puede cambiar con `TOKEN_TYPE`:

```
make token
TOKEN_TYPE=access make token
TOKEN_TYPE=refresh make token
TOKEN_TYPE=all make token
```

No imprimir tokens en logs compartidos, PRs ni documentación. Para validar el
flujo sin exponer el token:

```
TOKEN=$(make -s token); echo ${#TOKEN}
```

### Dependencias

Los `requirements.txt` están pineados con versiones exactas. El bundling de CDK
instala `backend/requirements.txt` directamente, así que no agregar dependencias
de desarrollo/local al runtime Lambda.

---

## Migraciones DynamoDB

- **Schema** (tablas, GSIs): gestionado por CDK — `cdk deploy` aplica cambios
- **Datos** (seeds, backfills): módulos en `migrations/versions/v0001_descripcion.py`
- Cada migración exporta `MIGRATION_ID`, `DESCRIPTION` y `run(context) -> MigrationResult`
- Registrar migraciones nuevas en `migrations/registry.py` en orden estricto
- La definición compartida de migración vive en `migrations/definition.py`; los puertos
  del runner no deben importar el registry concreto
- El runner trackea migraciones aplicadas en `MIGRATIONS_TABLE` con estados
  `IN_PROGRESS`, `SUCCESS` y `FAILED`
- `IN_PROGRESS` usa `lock_expires_at`; si el lock vence, otro deploy puede reintentar
  la migración sin intervención manual
- El Lambda `codelabs-billing-{env}-migrations` no tiene ruta HTTP pública; CI/CD lo
  invoca directamente después de desplegar el stack API
- Las migraciones deben ser idempotentes: si el dato ya existe, deben reportarlo como
  `skipped` y no fallar el deploy
- Para seeds de catálogos con identidades naturales (`slug`, `ruc`, etc.), la
  idempotencia debe validar también el dato existente, no solo el estado en
  `MIGRATIONS_TABLE`. Ejemplo: `0001_seed_plans` hace `get_by_slug()` antes de
  crear para no duplicar datos legacy que existan sin lock de unicidad.
- La tabla `MIGRATIONS_TABLE` es memoria de ejecución por ambiente: una migración
  en `SUCCESS` no se vuelve a ejecutar en cada deploy. Si se corrige la lógica de
  una migración ya aplicada, se debe crear una nueva migración correctiva o hacer
  una limpieza manual controlada; no reusar silenciosamente el mismo `MIGRATION_ID`.

---

## Historial de cambios relevantes

### 2026-06-07 — FrontendStack: S3 + CloudFront + Certificate

- `infra/stacks/certificate_stack.py` — ACM cert en us-east-1 (requerido por CloudFront),
  validación DNS automática via Route53, expone `self.certificate` via `cross_region_references`
- `infra/stacks/frontend_stack.py` — S3 privado con OAC; cache policy SPA (default TTL=0,
  CloudFront respeta Cache-Control del objeto); behavior `/api/*` con CloudFront Function
  que elimina el prefijo antes de reenviar a API Gateway; 403/404 → index.html para SPA
  routing; Route53 A + AAAA alias a CloudFront; `PRICE_CLASS_ALL` (incluye SA edge)
- `infra/app.py` — CertificateStack (us-east-1) + FrontendStack (sa-east-1) registrados
- `infra/cdk.context.json` — lookup us-east-1 del hosted zone cacheado
- `deploy-dev.yml` — nuevo job `deploy-frontend-infra` (infra changes → despliega ambos
  stacks); `deploy-frontend` lee bucket y distribution ID de CloudFormation (no necesita
  secret `FRONTEND_BUCKET_NAME`); invalidación CloudFront `/*` al finalizar el sync

### 2026-06-06 — Rebuild completo desde cero
- Arquitectura migrada de Aurora + VPC a DynamoDB sin VPC
- Costo dev reducido de ~$90/mes a < $2/mes
- Plantilla base Lambda implementada: `_base/` + `shared/`
- Clean Architecture: domain desacoplado de infra en cada Lambda
- Frontend migrado de Vite React a Expo Router (web + iOS + Android)
- Auth: Cognito SRP via Lambda propio — frontend nunca llama Cognito directo

### 2026-06-07 — Lambda auth — login SRP, refresh, logout, challenge

- `lambdas/auth/` implementado con Clean Architecture completa: domain / use_cases / infra
- 4 rutas públicas (sin JWT authorizer): `POST /auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/challenge`
- SRP puro en Python sin dependencias extra (`infra/srp.py` — adaptado de `scripts/make_token.py`)
- `IAuthProvider` (ABC) en `domain/repositories/` — dominio no conoce Cognito
- `CognitoAuthProvider` acepta `idp=None` en constructor — permite inyectar cliente mock en tests sin parchear boto3
- `AuthChallenge.parameters` sanitiza `SALT`, `SRP_B`, `SECRET_BLOCK` antes de enviar al frontend
- `ChallengeRequest.responses` es `dict[str,str]` genérico — soporta cualquier challenge futuro sin cambiar el schema
- `logout` es best-effort: `NotAuthorizedException` de Cognito (token ya inválido/expirado) se ignora silenciosamente
- `_provider = CognitoAuthProvider()` al cold start directo — sin lazy singleton global
- `MigrationAlreadyRunningError` movida de infra a `ports.py` — pertenece al contrato del puerto

### 2026-06-07 — Runner de migraciones
- Lambda worker de migraciones agregado al stack API
- `0001_seed_plans` migrado al runner idempotente con estado en DynamoDB
- `0001_seed_plans` reforzado con pre-check por slug para no duplicar planes legacy
  que existan sin `PLAN_SLUG#{slug}`
- Limpieza controlada en dev: se dejaron 5 planes canónicos + 5 locks de slug; los
  duplicados creados por el primer run fueron eliminados preservando referencias de tenants

### 2026-06-06 — Endurecimiento backend inicial
- RUC de tenants protegido con lock transaccional DynamoDB (`RUC#{ruc}`)
- Idempotencia HTTP convertida a reserva atómica ligada a método, path y hash de body
- Mutaciones de tenants cerradas con transacción única: entidad + audit + outbox + idempotencia
- Outbox transaccional agregado para desacoplar Cognito/SQS del request HTTP
- DynamoDB Local eliminado; local usa tablas AWS dev gestionadas por CDK
- JSON inválido y query params inválidos devuelven `VALIDATION_ERROR` en vez de 500
- Contraseñas temporales de onboarding ocultas de CloudWatch; entrega vía Cognito invitation
- CORS movido a configuración CDK e incluye `x-idempotency-key`
- Requirements pineados por capa: backend runtime, local server e infra CDK
- `local/.env.example` versionable y `scripts/create_superadmin.py` local/ignorado

### 2026-06-06 — Pruebas unitarias por Lambda
- `make test` agregado con `unittest discover`
- Tests unitarios para `_base`: parser e idempotencia
- Tests unitarios para `tenants`: use cases y handler HTTP
- Tests unitarios para workers: `tenant_onboarding` y `outbox_relay`
- Fakes centralizados en `backend/tests/unit/support.py` para evitar AWS real

### 2026-06-06 — email_notifications worker + Brevo
- Nuevo Lambda `workers/email_notifications`: envía email de bienvenida via Brevo al crear un tenant
- Patrón ports/adapters: `EmailSender` ABC + `BrevoEmailSender` (urllib3, sin deps extra)
- API key de Brevo en Secrets Manager (`codelabs-billing-dev/brevo-api-key`); nunca en env vars
- `tenant_onboarding` refactorizado: `EventPublisherPort` ABC + `OwnerCreatedEvent` con `temp_password`
- `cognito_identity_provider` usa `MessageAction="SUPPRESS"` — Brevo reemplaza el email nativo de Cognito
- `temp_password` viaja en SQS cifrado con CMK propio (KMS); nunca se loguea
- Cola `email-notifications` con CMK KMS independiente + DLQ; retención 1 día (datos sensibles corta vida)
- `ApiStack` despliega el Lambda `email_notifications` con trigger SQS y grant Secrets Manager
- Flujo completo: `POST /tenants` → outbox → `OutboxRelay` → SQS `tenant-onboarding` → Cognito (SUPPRESS) → SQS `email-notifications` → Brevo
- Tests unitarios cubren happy path, usuario existente, Brevo falla y partial batch failure

### 2026-06-06 — Endurecimiento plans y onboarding
- Mutaciones de `plans` pasan a `@idempotent` y commit transaccional: plan + audit + idempotency
- Slug de plan protegido con lock transaccional `PLAN_SLUG#{slug}`; el GSI queda solo para lectura
- Precios de planes migrados a `Decimal`; API y DynamoDB usan string decimal exacto
- `POST /tenants` valida `plan_id` contra un plan existente y activo antes de crear la empresa
- Onboarding de tenant reintenta entrega de credenciales reseteando contraseña temporal solo si Cognito sigue en estado de onboarding
- Brevo no loguea snippets de respuesta; valores de HTML escapados antes de enviar
- `local/.env.example` incluye `PLANS_TABLE` y `EMAIL_NOTIFICATIONS_QUEUE_URL`

### 2026-06-07 — Token local superadmin por SRP
- `make superadmin` agregado para crear/sincronizar el superadmin en Cognito desde `local/.env`
- `make token` agregado para obtener token Cognito via `USER_SRP_AUTH` sin enviar password en texto plano
- `scripts/make_token.py` implementa SRP compatible con Cognito y usa `COGNITO_*`, `SUPERADMIN_*`, `AWS_PROFILE`, `AWS_REGION` y `ENV`
- `scripts/create_superadmin.py` deja de tener credenciales hardcodeadas y pasa a consumir env vars
- `local/.env` conserva credenciales locales ignoradas por Git; `local/.env.example` solo documenta nombres vacíos

### 2026-06-07 — Fix doble serialización DynamoDB en transact_write_items
- `resource.meta.client` (obtenido via `table.meta.client`) hereda los handlers de TypeSerializer
  registrados por la sesión de boto3 al crear un resource. Llamar a `transact_write_items` a través
  de este cliente con items ya serializados (`{"S": "..."}`) los re-serializa como `{"M": {...}}`,
  causando `ValidationError: Type mismatch`.
- **Regla permanente:** los items pasados a `transact_write_items` via `resource.meta.client` deben
  ser Python puro (sin TypeSerializer). boto3 serializa una sola vez. No usar `_serialize()` ni
  `TypeSerializer` para construir los TransactItems — solo para operaciones que usen el cliente
  standalone (`session.client('dynamodb')`).
- Se eliminaron `TypeSerializer`, `_serializer` y `_serialize()` de todos los módulos que construyen
  transact items: `tenant_repository`, `plan_repository`, `idempotency`, `outbox`, `audit`.
- También se corrigieron palabras reservadas DynamoDB sin escapar en expression strings:
  `id`, `version`, `response`, `ttl`, `method`, `path`, `body_hash` → usar `#alias` en
  `ExpressionAttributeNames`. Esto aplica a `UpdateExpression` y `ConditionExpression` en el
  cliente low-level; las operaciones de alto nivel (`table.update_item`) manejan esto via `Attr()`.

### 2026-06-07 — Auditoría exhaustiva AST — Fase 1 y 2 (correcciones importantes)

- `plan_repository._transact_write`: inspecciona `cancellation_reasons` por índice (slug lock vs plan
  vs otro error) en lugar de lanzar `PlanSlugExistsError` para cualquier cancelación.
- `plan_catalog`: desacoplado de `lambdas.plans.*` — hace `get_item` directo a la tabla de planes
  sin importar del Lambda de plans; elimina acoplamiento estructural entre Lambdas independientes.
- `create_plan`: eliminado pre-check TOCTOU del slug (`_slug_exists`); la transacción ya garantiza
  unicidad atómica con el lock item `PLAN_SLUG#{slug}`.
- `tenant_repository.list()`: filtro explícito `Attr("entity_type").eq("TENANT")` en vez de depender
  del comportamiento implícito de DynamoDB con lock items sin campo `deleted`.
- `brevo_email_sender`: valida formato del API key de Secrets Manager — parsea JSON si el secreto
  fue almacenado como `{"api_key": "xkeysib-..."}` en lugar de string plano.
- `FakeTenantRepository.get_by_id`: lanza `TenantNotFoundError` correctamente en vez de `KeyError`.
- Tests de handler tenants: añadidos `GET /tenants`, `GET /tenants/{id}`, `GET 404`, update y toggle.
- Tests de handler plans: añadidos update happy path y update 404.
- `from __future__ import annotations`: se mantiene en todos los archivos — es requerido cuando
  métodos de clase sombreen builtins como `list` o `dict` (e.g., `IPlanRepository.list`).
- `audit/writer.py`: TTL de 7 años (retención legal SRI Ecuador).
- `SQSEventPublisher`: wrapper innecesario eliminado; reemplazado por `EventPublisher` directo
  (luego corregido a adaptador correcto en segunda auditoría).
- `shared/decorators/retry.py`: dead code eliminado.
- `TenantUpdatedEvent`, `TenantDeletedEvent`, `TenantStatusChangedEvent`: eliminados de use cases
  hasta que haya consumidores reales — no generar outbox items que siempre quedan SKIPPED.

### 2026-06-07 — Auditoría exhaustiva AST — Segunda pasada (correcciones críticas)

- **Race condition idempotencia** (`_base/idempotency.py`): `_reserve()` retornaba `None` cuando
  detectaba un item COMPLETED durante `ConditionalCheckFailedException`, haciendo que `@idempotent`
  re-ejecutara el handler. Fix: `_reserve()` lanza `_AlreadyCompleted` (excepción interna privada)
  que el decorador captura y convierte en devolución de la respuesta cacheada. Test de regresión
  con `RaceConditionTable` añadido.
- **CDK AuditTable sin TTL** (`infra/stacks/database_stack.py`): campo `ttl` escrito por
  `shared/audit/writer.py` era ignorado por DynamoDB. Se agrega `time_to_live_attribute="ttl"`.
- **`plan_repository.list()` sin paginación**: `scan()` sin `LastEvaluatedKey` → truncación
  silenciosa a 1MB. Se agrega loop de paginación completo.
- **`ITenantRepository.delete()`** eliminado de interfaz, implementación y fake — era código muerto
  que usaba `save()` en lugar de `commit()` con contexto transaccional completo.
- **`ITenantRepository.commit(**kwargs)`** sin tipado → firma keyword-only tipada, igual que
  `IPlanRepository.commit()`.
- **`SQSEventPublisher` recreado como adaptador correcto**: `tenant_onboarding` handler usaba
  `EventPublisher` concreto de `shared/`, rompiendo la inversión de dependencias. Ahora
  `SQSEventPublisher(EventPublisherPort)` adapta `EventPublisher` al puerto del worker.
- **`outbox_relay`**: comentario explícito del riesgo at-least-once — si `_mark_published` falla
  tras `send_message`, el retry de Lambda duplica el mensaje. Workers downstream deben ser
  idempotentes obligatoriamente.

### Notas de diseño permanentes (segunda auditoría — decisiones no cambiadas)
- **Ventana de 48h en `_reserve()`**: `Attr("ttl").lt(...)` permite re-reservar items cuyo TTL
  expiró pero DynamoDB aún no borró (puede tardar hasta 48h). Comportamiento intencional y correcto.
- **Lock items de slug sin limpieza**: `PLAN_SLUG#{slug}` persiste indefinidamente. Si en el futuro
  se implementa soft delete de planes, los slugs no podrían reutilizarse sin un flujo explícito de
  reactivación (igual que el lock de RUC en tenants). Decisión de diseño explícita.

## Deuda técnica identificada

- Implementar Lambdas pendientes: `clients`, `invoices`, `workers` adicionales.
- Agregar tests unitarios para `lambdas/auth/` (use cases y handler).
- Agregar migraciones de datos cuando existan tenants previos sin lock `RUC#{ruc}`.
- Agregar pruebas de integración contra AWS dev cuando se cierre el primer flujo end-to-end.
- Cuando se implemente soft delete de planes: definir flujo explícito de reactivación de slug
  (análogo al flujo de reactivación de RUC en tenants) en lugar de recreación silenciosa.
- Actualizar `EXPO_PUBLIC_API_URL=""` en el frontend para usar routing unificado via CloudFront
  (el behavior `/api/*` ya existe — solo falta cambiar la URL en la app).

### CloudFront path routing — implementado en FrontendStack (2026-06-07)

El behavior `/api/*` ya está en producción. El frontend puede llamar `/api/tenants`
(mismo origen) en lugar del dominio directo. Cambiar `EXPO_PUBLIC_API_URL=""` activa
el routing unificado y elimina CORS completamente.
