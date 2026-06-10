# CodeLabs Billing Cloud

Indice y reglas no negociables. Patrones de construccion y reglas de negocio viven en
`context/` (ver tablas abajo) — leerlos segun la tarea.

Ultima actualizacion: 2026-06-10.

## Objetivo Del Producto

SaaS ecuatoriano de facturacion electronica multitenant.

El sistema administra:

- `tenants`: empresas que contrataron el SaaS.
- `plans`: catalogo comercial y limites del SaaS.
- `clients`: compradores/clientes dentro de cada tenant.
- `auth`: login Cognito SRP expuesto por Lambda.
- `workers`: onboarding, emails, migraciones y outbox async.

No existe todavia un Lambda `invoices`. Cuando se implemente, debe respetar las reglas SRI
y no mezclar "Consumidor Final" con `clients` (ver `context/CLIENTS.md`).

Cuenta GitHub: `FrancisU20`.
AWS profile del proyecto: `codelabs`.
Region principal: `sa-east-1`.

## Estado Actual

Implementado: CRUD y filtros server-side de `tenants`, `plans` y `clients`. Paginacion
opaca, idempotencia HTTP, locks transaccionales, outbox transaccional, separacion
publica/admin de planes.

Proximo hito: **onboarding self-service** — registro publico del tenant con seleccion
de plan y carga de certificado digital p12. Ver `context/ONBOARDING.md`.

## Memorias Base

Patrones de construccion transversales. Leer **siempre** antes de tocar codigo de esa capa:

| Archivo | Cubre |
| --- | --- |
| `context/BACKEND.md` | Clean Architecture, `_base`/`shared`, contrato HTTP, DynamoDB, idempotencia, outbox, migraciones |
| `context/FRONTEND.md` | Estructura, design system, componentes compartidos, routing, patrones de pantalla |

## Memorias Por Dominio

Reglas de negocio, flujos y DynamoDB especificos de cada dominio (incluye su seccion Frontend):

| Archivo | Cubre |
| --- | --- |
| `context/AUTH.md` | Login SRP, JWT claims, roles, challenge flow |
| `context/TENANTS.md` | Entidad Tenant, maquina de estados, RUC lock, plan_status |
| `context/PLANS.md` | Catalogo de planes, slug lock, endpoints publico vs admin |
| `context/CLIENTS.md` | Clientes del tenant, tipos de identificacion, lock de identificacion |
| `context/ONBOARDING.md` | Registro self-service, certificados p12, entornos SRI (pruebas/produccion) |
| `context/INVOICES.md` | Emision de documentos, numeracion SRI, XAdES-BES, batch jobs (**pendiente**) |

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

## Estructura Del Monorepo

```text
backend/    # Lambdas + shared + migrations + tests       -> context/BACKEND.md
frontend/   # Expo Router app                              -> context/FRONTEND.md
infra/      # CDK stacks (stacks/, config/)                -> context/BACKEND.md
```

## Comandos De Validacion

Ejecutar desde la raiz salvo indicacion contraria.

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

Nunca imprimir tokens, passwords ni secretos en logs. Para validar token sin exponerlo:

```bash
TOKEN=$(make -s token); echo ${#TOKEN}
```

## Reglas De Git Y Deploy

- No hacer `git push` sin confirmacion explicita.
- No agregar `Co-Authored-By` en commits.
- El deploy normal es por GitHub Actions.
- `cdk deploy` local solo si el usuario lo pide explicitamente.
- Docs-only en raiz (`*.md`), `docs/**` y `postman/**` no deberian disparar deploy pesado.
- Ojo: cambios bajo `frontend/**` se clasifican como frontend aunque sean `.md`.

Workflows:

- `develop` → dev.
- `release/**` o dispatch manual → staging.
- `master` con `workflow_dispatch` protegido → prod.

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

Variables relevantes para superadmin/token:

```text
SUPERADMIN_EMAIL=...
SUPERADMIN_PASSWORD=...
COGNITO_USER_POOL_ID=...
COGNITO_WEB_CLIENT_ID=...
```

`make superadmin` es idempotente: crea o actualiza usuario superadmin Cognito.
`make token` usa `USER_SRP_AUTH` y por defecto imprime `IdToken`.

## Como Agregar Un Feature

**Paso 0 — Leer antes de escribir codigo:**

- Este archivo — reglas no negociables.
- `context/BACKEND.md` y/o `context/FRONTEND.md` segun la capa que toques.
- El archivo de dominio del feature (ej. `context/INVOICES.md`). Si no existe, crearlo
  en `context/` antes de empezar, con la seccion "Lee Tambien Antes De Empezar" primero.

Los pasos de implementacion detallados estan en `context/BACKEND.md` (backend) y
`context/FRONTEND.md` (frontend).

## Antes De Cerrar Cualquier Cambio

1. Revisar `git status --short`.
2. No revertir cambios ajenos.
3. Correr validaciones relevantes.
4. Si tocaste backend: `make test` y ruff.
5. Si tocaste frontend: `format:check`, `typecheck`, `lint`, `test:run`;
   si cambia build/routing, tambien `build:web`.
6. Reportar lo que cambiaste, pruebas ejecutadas y cualquier riesgo residual.
7. Si cambiaste reglas o flujos de un dominio: actualizar el archivo `.md` de ese dominio.
8. Si cambiaste un patron transversal: actualizar `context/BACKEND.md` o `context/FRONTEND.md`.
