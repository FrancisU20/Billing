# Wali

Indice y reglas no negociables. Patrones de construccion y reglas de negocio viven en
`context/` (ver tablas abajo) — leerlos segun la tarea.

Marca de producto: **Wali**. La entidad legal operadora sigue siendo CodeLabs Ecuador
(ver textos legales en `frontend/features/marketing/content/legal.ts`). Los identificadores
internos de infra (stacks CDK, tablas, buckets, secrets, Cognito, perfil AWS `codelabs`)
siguen con el prefijo `codelabs-billing` / `CodeLabsBilling` a proposito: son recursos AWS
ya desplegados y renombrarlos implicaria recrearlos (ver `context/BACKEND.md` y
`context/INVOICES.md` para el detalle de cada recurso). No renombrar esos identificadores
sin antes planear una migracion de datos/secrets.

Excepcion: los **dominios publicos** (`wali-{env}.codelabsecuador.com` /
`api-wali-{env}.codelabsecuador.com`, ver tabla en `context/BACKEND.md`) si cambiaron de
`billing-*` a `wali-*` y ya estan desplegados en dev (2026-06-21) — los nombres fisicos de
infra y los dominios publicos son decisiones independientes.

Ultima actualizacion: 2026-06-21.

## Objetivo Del Producto

SaaS ecuatoriano de facturacion electronica multitenant.

El sistema administra:

- `tenants`: empresas que contrataron el SaaS.
- `plans`: catalogo comercial y limites del SaaS.
- `clients`: compradores/clientes dentro de cada tenant.
- `products`: catalogo vendible del tenant (productos, servicios, paquetes, membresias).
- `auth`: login Cognito SRP expuesto por Lambda.
- `workers`: onboarding, emails, migraciones y outbox async.
- `subscriptions`: pagos dLocal Go SmartFields por ciclo de plan de la suscripcion SaaS.

El dominio `invoices/documents` tiene su **MVP completo** (Sprints 1-6). Arquitectura
completa documentada en `context/INVOICES.md`: Lambdas `sequences`, `documents` e
`invoice_processor`; tablas DynamoDB `sequences`, `documents`, `batch_jobs`; S3 con
Object Lock; colas SQS separadas sign/poll (compartidas + dedicadas enterprise
pendiente de auto-provision); frontend de emision/listado/detalle de documentos y
gestion de establecimientos; emails al emisor y entrega idempotente al comprador con
XML autorizado + RIDE adjuntos.
Regla critica: no mezclar "Consumidor Final" con `clients` (ver `context/CLIENTS.md`).

Cuenta GitHub: `FrancisU20`.
AWS profile del proyecto: `codelabs`.
Region principal: `sa-east-1`.

## Estado Actual

Implementado: CRUD y filtros server-side de `tenants`, `plans` y `clients`; auth SRP via
Lambda; onboarding publico con OTP sin pago (modelo Netflix — cuenta se crea siempre, plan
de pago queda `subscription_status='pending_payment'`); validacion/carga/reemplazo de
certificados p12; emails transaccionales con link de renovacion directo; workers (vencimiento
de certificados, recordatorio/vencimiento de suscripcion, pagos huerfanos, reconciliador
de activaciones pendientes cada 5 min); paginacion opaca, idempotencia HTTP, locks
transaccionales, outbox transaccional y separacion publica/admin de planes; dLocal Go
SmartFields completo (create + confirm + refund + webhooks HMAC-SHA256); manejo de 3DS
(redirect URL del banco + polling); formulario de pago con datos del pagador independientes
del perfil del tenant; guard `pending_payment` con auto-activate via `pending_order_id` +
`PendingActivationBanner`; retry con backoff exponencial en activate y renew; endpoint de
activacion (`POST /tenants/{id}/subscription/activate`) con Phase 1 pre-save de
`pending_order_id`; endpoint de renovacion; endpoint de reembolso superadmin; pagina de
billing en frontend; **markup 12%** sobre precio neto del plan (`shared/billing.py`,
`gross_price()`); pantalla de activacion sin boton intermedio (auto-crea order al montar)
con `PriceBreakdown` (plan + comision + total); **cobro automatico** en worker de renovacion
via `dlocal_payer_id` guardado con estado `payment_failed` si falla + email de accion
requerida; endpoint `POST /tenants/{id}/subscription/retry-payment` (tarjeta guardada,
402 si rechazada); `PaymentFailedBanner` con reintento automatico y opcion de nueva tarjeta;
**6 bugs de auditoría resueltos** (scan payment_failed, guard PENDING en confirm, webhook
order_id, mark_applied_to_tenant condition, type hint RetryPaymentUseCase, safe datetime).

Products — Sprint 1: CRUD tenant-scoped de productos/servicios con `product_id` estable,
SKU editable unico por tenant, tipo vendible, precio/IVA default y stock opcional modelado.
El facturador puede seleccionar o crear rapidamente un producto; la factura persiste snapshot
legal de linea para que cambios futuros al catalogo no alteren documentos emitidos.
**Sprint 2 completo (descuentos):** 2a `discount_percentage` (0-100%, opcional) por
producto, expuesto en CRUD. 2b campana de descuento global por tenant (`GET/PUT
/products/discount-campaign`, singleton `active`+`percentage`, solo `owner|admin` la
configura). 2c+2d techo de descuento `max(producto%, campana%)` validado en `documents`
(no en `products`, ver `context/INVOICES.md`) para toda linea con/sin `product_id`, con
override auditado (`override_discount_ceiling`+`override_reason`, sin rol adicional
porque emitir ya es `owner|admin|superadmin`). 2e RIDE muestra `$desc (%)` + columna
Subtotal por linea.

Invoices/documents — MVP completo (Sprints 1-6): infra CDK (tablas, S3 Object Lock,
colas sign/poll); Lambda `sequences` (establecimientos + puntos de emision, punto 099
de pruebas); Lambda `documents` (emision individual, reserva de secuencial, clave de
acceso, encolado SIGN); Lambda `invoice_processor` (firma XAdES-BES RSA-SHA1/SHA1/
C14N 1.0, SOAP recepcion/autorizacion SRI, RIDE con reportlab, S3 con LegalHold,
reintentos con backoff, 3 eventos de email al tenant via `email_notifications`,
notificacion idempotente al comprador con XML autorizado + RIDE adjuntos);
frontend (`features/documents` + `features/sequences`): listado/emision/detalle de
documentos con poll automatico mientras PENDING/PROCESSING, descarga de RIDE, selector
de comprador con picker de clientes existentes, gestion de establecimientos y puntos
de emision en `/settings/estab`. Fixes reales contra SRI testing confirmados:
`SOAPAction=""`, `dirEstablecimiento` obligatorio, declaracion XML con comillas dobles
y digito de ambiente `1=pruebas`/`2=produccion` tanto en XML como en clave de acceso.

**UX Refactor & Operability Roadmap completado** (sprints 0-7): freshness de listados,
paginacion por pagina, busqueda reactiva, filtros minimalistas, calendario, validacion en
vivo, dashboard real, acciones rapidas `active/inactive`, formularios de creacion/edicion
amigables, consistencia visual de descuentos, reorganizacion de modulos y centralizacion
final de componentes (`StatMetric`, `ListScreenHeader`, `ListCell`, `EntityAvatar`,
`PickerModal` — ver tabla de `FRONTEND.md`). Aplico a toda la app: tenant
(`owner/admin/viewer`), superadmin, auth/onboarding y modulos futuros; no solo al
dashboard tenant. Nota de Credito (04), auto-provision de colas enterprise y batch masivo
quedan pendientes salvo cambio de prioridad (no eran parte de este roadmap).
Dashboard tenant real implementado via `GET /documents/summary` (conteos del mes, total
autorizado y consumo del limite mensual del plan con barra de progreso). Hub "Mi empresa"
(`/settings/company`) agrupa datos de empresa (self-edit), certificado digital y accesos a
establecimientos/descuento global/facturacion; menu principal tenant quedo con un solo
item de configuracion en vez de tres; `BillingScreen` ya no permite pago manual cuando la
suscripcion esta `active` (muestra card "todo bien" en su lugar). Dashboard superadmin
implementado (`GET /superadmin/dashboard`): ingresos del mes/año, MRR estimado,
membresias activas/inactivas, tenants nuevos del mes, tenants por ambiente SRI y plan mas
vendido, con tendencias % vs periodo anterior (solo donde es honesto sin snapshot
historico), grafico de evolucion de ingresos de 30 dias (SVG propio), barras de
distribucion y card de tenants recientes — ver `TENANTS.md` seccion "Dashboard
Superadmin — Implementado".

## Memorias Base

Patrones de construccion transversales. Leer **siempre** antes de tocar codigo de esa capa:

| Archivo                  | Cubre                                                                                                                                     |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `context/BACKEND.md`     | Clean Architecture, `_base`/`shared`, contrato HTTP, DynamoDB, idempotencia, outbox, migraciones                                          |
| `context/FRONTEND.md`    | Estructura, design system, componentes compartidos, routing, patrones de pantalla                                                         |

## Memorias Por Dominio

Reglas de negocio, flujos y DynamoDB especificos de cada dominio (incluye su seccion Frontend):

| Archivo                    | Cubre                                                                                                                                       |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `context/AUTH.md`          | Login SRP, JWT claims, roles, challenge flow                                                                                                |
| `context/TENANTS.md`       | Entidad Tenant, maquina de estados, RUC lock, plan_status                                                                                   |
| `context/PLANS.md`         | Catalogo de planes, slug lock, endpoints publico vs admin                                                                                   |
| `context/CLIENTS.md`       | Clientes del tenant, tipos de identificacion, lock de identificacion                                                                        |
| `context/PRODUCTS.md`      | Catalogo vendible, SKU, stock opcional e integracion con facturas                                                                           |
| `context/ONBOARDING.md`    | Registro self-service con OTP, certificados p12, lead Enterprise                                                                            |
| `context/CERTIFICATES.md`  | Validacion, almacenamiento y ciclo de vida de certificados digitales p12                                                                    |
| `context/INVOICES.md`      | Emision documentos SRI, secuenciales, XAdES-BES, invoice_processor, S3 WORM, frontend y emails al comprador (**MVP completo, Sprints 1-6**) |
| `context/SUBSCRIPTIONS.md` | Suscripcion SaaS via dLocal Go SmartFields, modelo Netflix, webhooks, 3DS, reembolso, resiliencia 4 capas (**completo**)                    |

## Mapa De Deuda Tecnica

La deuda tecnica vive en la seccion `## Deuda Tecnica` del archivo de contexto que
corresponda. Estado actual por capa/dominio:

| Archivo                    | Deuda relevante                                                                                                                                                                                                                                                                                                                                 |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `context/FRONTEND.md`      | `SelectField` sin construir; tests de render de componentes bloqueados por infra (`vitest` no parsea `react-native`); busquedas backend a escala (`q` in-memory en products/documents, sin GSI) pendientes                                                                                                                                     |
| `context/AUTH.md`          | Sin tests de integracion Cognito real; evaluar rotacion de refresh token                                                                                                                                                                                                                                                                        |
| `context/TENANTS.md`       | Listado admin con scan para alta cardinalidad/dashboard; Scan completo de `payments` para ingresos del dashboard superadmin sin techo (a diferencia de `tenants`, catalogo chico) — revisar si el volumen de pagos crece mucho                                                                                                                  |
| `context/PLANS.md`         | `list()` con scan completo aceptable solo para catalogo chico                                                                                                                                                                                                                                                                                   |
| `context/CLIENTS.md`       | Busqueda `q` y validacion batch no escalan para cargas masivas                                                                                                                                                                                                                                                                                  |
| `context/PRODUCTS.md`      | Inventario avanzado con movimientos/reservas queda para sprint futuro                                                                                                                                                                                                                                                                           |
| `context/ONBOARDING.md`    | Queue dedicada Enterprise automatica es alcance futuro                                                                                                                                                                                                                                                                                          |
| `context/CERTIFICATES.md`  | Movil nativo, ampliacion de CAs y costo a escala son decisiones futuras                                                                                                                                                                                                                                                                         |
| `context/INVOICES.md`      | Literal SOAP de rechazo sin verificar contra SRI real; RIDE sin barcode/logo; clasificacion de errores SRI parcial; colas dedicadas enterprise sin auto-provision; `invoice_processor` sin concurrencia reservada (cuenta AWS limitada a 10 ejecuciones concurrentes en `sa-east-1`)    |
| `context/SUBSCRIPTIONS.md` | Scans en workers (aceptable hasta ~10 K); webhook sin DLQ; orders PENDING (3DS) sin limpieza automatica                                                                                                                                                                                                                                         |

## Stack

| Capa           | Tecnologia                                   |
| -------------- | -------------------------------------------- |
| Backend        | Python 3.12, Lambda ARM64                    |
| API            | HTTP API Gateway + JWT authorizer Cognito    |
| Auth           | Amazon Cognito, SRP ejecutado por Lambda     |
| DB             | DynamoDB on-demand, multi-table              |
| Async          | SQS + DynamoDB Streams + Outbox              |
| Infra          | AWS CDK Python                               |
| Frontend       | Expo Router v56, React Native 0.85, React 19 |
| Tests backend  | `unittest` + fakes, sin AWS real             |
| Tests frontend | Vitest + TypeScript + ESLint                 |

## Estructura Del Monorepo

```text
backend/    # Lambdas + shared + migrations + tests       -> context/BACKEND.md
frontend/   # Expo Router app                              -> context/FRONTEND.md
infra/      # CDK stacks (stacks/, config/)                -> context/BACKEND.md
```

## Antes De Hacer Push — Regla No Negociable

**`make ci` debe pasar en verde antes de cualquier push o PR.**

Es el espejo exacto de `pr-checks.yml`. Si falla aqui, fallara en CI y bloqueara el PR.
No hay excepcion: ni "es solo docs", ni "es un hotfix pequeno".

```bash
make ci          # corre todo: lint, security, tests, frontend, cdk
make ci-backend  # solo backend (lint + format + tests + coverage)
make ci-security # solo bandit + pip-audit
make ci-frontend # solo frontend (format + lint + typecheck + tests)
make ci-cdk      # solo validacion CDK
```

Prerequisito una sola vez: instalar deps de CI en el venv local:

```bash
backend/.venv/bin/pip install -r backend/requirements-ci.txt
```

## Comandos Utiles

```bash
make test        # tests rapidos sin coverage (para iterar en desarrollo)
make superadmin  # sincroniza superadmin Cognito desde variables de entorno o .env
make token       # imprime ID token Cognito por defecto
```

Nunca imprimir tokens, passwords ni secretos en logs. Para validar token sin exponerlo:

```bash
TOKEN=$(make -s token); echo ${#TOKEN}
```

## Reglas De Git Y Deploy

- **`make ci` verde antes de cualquier push.** Ver seccion anterior.
- No hacer `git push` sin confirmacion explicita.
- No agregar `Co-Authored-By` en commits.
- `CLAUDE.md` y `context/` son memoria versionada de este proyecto personal; no ignorarlos.
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

1. Revisar `git status --short`. No revertir cambios ajenos.
2. Correr `make ci` y confirmar que pasa en verde.
3. Si `make ci` es lento y el cambio es acotado, como minimo:
   - Backend solo: `make ci-backend && make ci-security`.
   - Frontend solo: `make ci-frontend`.
   - Cualquier cambio en `infra/`: agregar `make ci-cdk`.
4. Reportar lo que cambiaste, que stages de CI se corrieron y cualquier riesgo residual.
5. Si cambiaste reglas o flujos de un dominio: actualizar el archivo `.md` de ese dominio.
6. Si cambiaste un patron transversal: actualizar `context/BACKEND.md` o `context/FRONTEND.md`.
