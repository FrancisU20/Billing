# Subscriptions — Dominio

Estado: **implementado Fase 4 completa** — dLocal Go SmartFields (create + confirm + status),
modelo Netflix (registro sin pago, activacion en primera sesion), endpoint de activacion
autenticado, endpoint de renovacion, worker diario de vencimiento con link `/billing` en email,
pagina de billing, webhook dLocal Go con HMAC-SHA256, endpoint de reembolso (superadmin),
manejo de 3DS en frontend (`use3dsFlow` hook) y guard flash fix en layout del tenant.

## Lee Tambien Antes De Empezar

Leer estos archivos en orden antes de escribir codigo en este dominio:

| Archivo | Por que |
| --- | --- |
| `CLAUDE.md` | Reglas no negociables (seguridad, git) |
| `BACKEND.md` | Patron `public_lambda_handler`, `get_secret_json`, Secrets Manager |
| `TENANTS.md` | Campos `dlocal_payer_id`, `subscription_status` en Tenant |
| `ONBOARDING.md` | Registro sin pago (modelo Netflix); tenant `pending_payment` al registrarse |

## Proposito

dLocal Go actua como pasarela de pago unico por ciclo de facturacion SaaS.
Se usa **SmartFields / Transparent Checkout** — formulario de tarjeta embebido en
la web, sin redireccion. El card token se genera en el browser via el SDK JS de
dLocal; nunca pasa por nuestros servidores (PCI DSS).

Distinto del dominio `INVOICES.md`, que sera la facturacion SRI que el tenant
emite a sus propios clientes.

## Flujo De Registro (Modelo Netflix)

El registro no requiere pago. La cuenta se crea siempre; el pago ocurre en la primera
sesion autenticada si el plan es de pago.

```
POST /onboarding/otp/confirm
  → plan gratis:  tenant creado, subscription_status=null  → dashboard
  → plan de pago: tenant creado, subscription_status='pending_payment', plan_cycle_ends_at=null
```

## Flujo De Activacion — Primera Sesion (plan de pago)

```
Frontend (app autenticada)  Backend              dLocal Go
   |                          |                    |
   | login → JWT               |                    |
   | (tenant)/_layout.tsx      |                    |
   | detecta pending_payment   |                    |
   | → redirect activate-sub   |                    |
   |                          |                    |
   |-- POST /subscriptions/payments (plan_id) ----->|
   |<-- { order_id, checkout_token, amount }        |
   | SDK SmartFields (checkout_token)              |
   | payer ingresa tarjeta → card_token             |
   |-- POST /subscriptions/payments/{order_id}/confirm
   |        { card_token, client_* }               |
   |<-- { status: "PAID", payer_id }               |
   |                          |                    |
   |-- POST /tenants/{id}/subscription/activate     |
   |         verifica pago PAID                    |
   |         activa suscripcion (cycle desde now)  |
   |<-- { plan_cycle_ends_at, subscription_status } |
   | → redirect dashboard                           |
```

## Flujo De Renovacion — Billing

```
Frontend (billing.tsx)   Backend                  dLocal Go
   |                       |                        |
   |-- POST /subscriptions/payments (plan_id) ------>|
   |<-- { order_id, checkout_token, amount }         |
   | SDK SmartFields (checkout_token)                |
   | payer ingresa tarjeta -> card_token             |
   |-- POST /subscriptions/payments/{order_id}/confirm
   |        { card_token, client_first_name,         |
   |          client_last_name, client_email,         |
   |          client_document_type, client_document } |
   |<-- { status: "PAID" }                          |
   |-- POST /tenants/{id}/subscription/renew         |
   |         marca pago aplicado (tenant_id fijo)    |
   |         extiende plan_cycle_ends_at             |
   |<-- { plan_cycle_ends_at, subscription_status }  |
```

Planes gratuitos (`monthly_price == 0 && annual_price == 0`) no activan la
pasarela — `CreatePaymentUseCase` lanza `FreePlanPaymentError` (422).
En el modelo Netflix, tenants con plan gratuito no tienen `subscription_status='pending_payment'`
y pasan directo al dashboard sin pantalla de activacion.

## Arquitectura

```
subscriptions/
  domain/
    commands.py          CreatePaymentCommand, ConfirmPaymentCommand
    errors.py            FreePlanPaymentError, PaymentNotFoundError, ...
    repositories/
      i_dlocal_client.py IDLocalClient (ABC), DLocalCreatePaymentResult, DLocalConfirmPaymentResult
      i_payment_repository.py  save(), get_by_order_id(), link_tenant(), link_tenant_transact_item()
      i_plan_catalog.py  PlanSummary (monthly_price, annual_price, limit_cycle, is_free)
    entities/
      payment.py         Payment (order_id, tenant_id, plan_id, checkout_token, plan_cycle, ...)
  infra/
    dlocal_client.py     DLocalClient(IDLocalClient): Bearer {api_key}:{secret_key};
                         create payment envia allow_transparent=true para SmartFields;
                         usa headers HTTP explicitos para evitar bloqueos WAF de dLocal
    payment_repository.py  DynamoDB (PK = "PAYMENT#{order_id}")
    plan_catalog.py      Lectura local de planes sin importar lambdas.plans.*
  use_cases/
    create_payment.py    CreatePaymentUseCase — llama dlocal.create_payment, persiste checkout_token
    confirm_payment.py   ConfirmPaymentUseCase — llama dlocal.confirm_payment con checkout_token
    get_payment.py       GetPaymentUseCase
  schemas.py             CreatePaymentRequest, ConfirmPaymentRequest
  handler.py             POST /subscriptions/payments
                         POST /subscriptions/payments/{order_id}/confirm
                         GET  /subscriptions/payments/{order_id}

# Activacion y Renovacion viven en tenants/ (endpoints autenticados):
backend/lambdas/tenants/
  domain/
    commands.py          ApplySubscriptionRenewalCommand (+ existing)
    errors.py            SubscriptionAlreadyActiveError, PaymentNotCapturedError,
                         PaymentAlreadyAppliedError, ... (+ existing)
    repositories/
      i_payment_reader.py     IPaymentReader (ABC) — lectura y mark_applied de Payment
      i_payment_verifier.py   IPaymentVerifier (ABC) — alias/extension de IPaymentReader
  use_cases/
    activate_subscription.py  ActivateSubscriptionUseCase — primera activacion pending_payment
    apply_subscription_renewal.py  ApplySubscriptionRenewalUseCase — renovacion de ciclo
  infra/
    payment_verifier.py    DynamoPaymentVerifier: verifica status PAID o AUTHORIZED

# Worker diario:
backend/lambdas/workers/subscription_renewal_notifier/
  handler.py             EventBridge cron(0 10 * * ? *)
  use_case.py            NotifySubscriptionRenewalUseCase
```

## Componentes Externos

- Lambda: `backend/lambdas/subscriptions/`
- Red: Lambda fuera de VPC; salida a internet administrada por AWS Lambda. No usar NAT
  dedicado para este flujo salvo que dLocal exija allowlist de IP fija.
- DynamoDB: tabla `payments` (PK=`id` = `"PAYMENT#{order_id}"`, GSI `tenant-payments-index`)
- Secrets Manager: `codelabs-billing-{env}/dlocalgo-credentials`
  JSON con `{"api_key": "...", "secret_key": "..."}` — creado manualmente por entorno
- SmartFields API Key: publica, expuesta en frontend via `EXPO_PUBLIC_DLOCALGO_SMARTFIELDS_KEY`
  (diferente a `api_key`/`secret_key` — es una clave SmartFields solicitada a soporte dLocal)

## Configuracion

| Variable de entorno | Valor dev/staging | Valor prod |
| --- | --- | --- |
| `PAYMENTS_TABLE` | (del stack) | (del stack) |
| `PLANS_TABLE` | (del stack) | (del stack) |
| `DLOCALGO_CREDENTIALS_NAME` | `codelabs-billing-dev/dlocalgo-credentials` | `codelabs-billing-prod/dlocalgo-credentials` |
| `DLOCALGO_API_URL` | `https://api-sbx.dlocalgo.com` | `https://api.dlocalgo.com` |

## API Contract

| Metodo | Ruta | Auth | Descripcion |
| --- | --- | --- | --- |
| POST | `/subscriptions/payments` | ninguna (publico) | Crea payment dLocal y registra Payment |
| POST | `/subscriptions/payments/{order_id}/confirm` | ninguna (publico) | Confirma pago con card_token |
| GET  | `/subscriptions/payments/{order_id}` | ninguna (publico) | Consulta estado del pago |
| POST | `/subscriptions/payments/{order_id}/refund` | JWT superadmin | Reembolsa pago PAID via dLocal |
| POST | `/subscriptions/webhooks/dlocal` | HMAC-SHA256 (ninguna JWT) | Recibe notificaciones asincronas de dLocal Go |
| POST | `/tenants/{id}/subscription/activate` | JWT (tenant owner/admin) | Activa suscripcion pending_payment (primera vez) |
| POST | `/tenants/{id}/subscription/renew` | JWT (tenant owner/admin) | Aplica renovacion de ciclo |

### POST /subscriptions/payments

Requiere `X-Idempotency-Key` (ver `BACKEND.md`).

Request:
```json
{ "plan_id": "uuid-plan", "currency": "USD" }
```

Response 201:
```json
{ "data": { "order_id": "DP-12345", "checkout_token": "mct_xxx", "amount": "5.99", "currency": "USD" } }
```

Errores: 422 `FREE_PLAN_NO_PAYMENT`, 404 `PLAN_NOT_FOUND`, 502 `PAYMENT_CREATION_FAILED`.

### POST /subscriptions/payments/{order_id}/confirm

Request:
```json
{
  "card_token": "tok_xxx",
  "client_first_name": "Juan",
  "client_last_name": "Pérez",
  "client_email": "buyer@example.com",
  "client_document_type": "CI",
  "client_document": "1712345678"
}
```

Response 200:
```json
{ "data": { "order_id": "DP-12345", "status": "PAID", "payer_id": "...", "payer_email": "...", "redirect_url": null } }
```

Errores: 404 `PAYMENT_NOT_FOUND`, 409 `PAYMENT_ALREADY_CONFIRMED`, 502 `PAYMENT_CONFIRM_FAILED`.

Si dLocal retorna `REJECTED` u otro status no-PAID, el pago queda en `FAILED` y el endpoint
responde 200 con `status: "FAILED"` para que el frontend pueda mostrar el rechazo sin
reintentar una confirmacion ya consumida.
Si dLocal retorna una respuesta estilo SmartFields sample (`success`/`payment_id` sin `status`),
el adapter normaliza `success=true` sin `redirect_url` a `PAID`.
Si dLocal requiere 3DS y retorna `redirect_url`, el pago local queda `PENDING` y el frontend
abre la URL en nueva pestaña (preserva estado de la app). El usuario vuelve y presiona
"Ya complete la verificacion" que dispara polling hasta 10 veces cada 3 s via
`GET /subscriptions/payments/{order_id}`. Ver hook `use-3ds-flow.ts`.

### GET /subscriptions/payments/{order_id}

Response 200:
```json
{ "data": { "order_id": "DP-12345", "status": "CREATED|PAID|FAILED|PENDING",
            "plan_id": "...", "plan_cycle": "month|year", "amount": "5.99", "currency": "USD",
            "tenant_id": null, "created_at": "...", "confirmed_at": "..." } }
```

Errores: 404 `PAYMENT_NOT_FOUND`.

### POST /subscriptions/payments/{order_id}/refund

Requiere JWT superadmin. Solo aplicable a pagos con status `PAID` o `AUTHORIZED`.

Response 200:
```json
{ "data": { "order_id": "DP-12345", "refund_id": "REF-xxx", "status": "REFUNDED" } }
```

Errores: 404 `PAYMENT_NOT_FOUND`, 409 `PAYMENT_NOT_REFUNDABLE`, 502 `PAYMENT_REFUND_FAILED`.

### POST /subscriptions/webhooks/dlocal

Endpoint publico (sin JWT). Autenticado via HMAC-SHA256:
- Header requerido: `X-Signature` — valor hex de `HMAC-SHA256(raw_body, secret_key)`
- Responde 403 si la firma falta o no coincide.

Payload esperado (eventos `PAYMENT`):
```json
{ "type": "PAYMENT", "data": { "order_id": "DP-12345", "status": "PAID|REJECTED|FAILED|CANCELLED" } }
```

Comportamiento: actualiza el status del Payment en DynamoDB solo si el status es terminal
(`PAID`/`APPROVED`→`PAID`, `REJECTED`, `FAILED`, `CANCELLED`) y distinto al actual.
Eventos con `type != "PAYMENT"` o sin `order_id` se responden 200 sin procesar.
Pagos no encontrados se ignoran (idempotente).

### POST /tenants/{id}/subscription/activate

Requiere `X-Idempotency-Key`. Solo valido cuando `subscription_status == 'pending_payment'`.

Request:
```json
{ "order_id": "DP-12345" }
```

Response 200:
```json
{ "data": { "tenant_id": "...", "plan_cycle_ends_at": "...", "subscription_status": "active" } }
```

Errores: 409 `SUBSCRIPTION_ALREADY_ACTIVE`, 422 `SUBSCRIPTION_RENEWAL_PAYMENT_NOT_CONFIRMED`,
409 `SUBSCRIPTION_RENEWAL_PAYMENT_ALREADY_APPLIED`, 422 `SUBSCRIPTION_RENEWAL_PLAN_MISMATCH`.

### POST /tenants/{id}/subscription/renew

Requiere `X-Idempotency-Key`.

Request:
```json
{ "order_id": "DP-12345" }
```

Response 200:
```json
{ "data": { "tenant_id": "...", "plan_cycle_ends_at": "...", "subscription_status": "active" } }
```

## DynamoDB Schema

Tabla: `payments`. PK = `id` (sin SK).

```
Payment CREATED:
  id              = "PAYMENT#{order_id}"
  order_id        = "DP-12345"         ← dLocal payment_id
  checkout_token  = "mct_xxx"          ← SmartFields token (para confirm)
  tenant_id       = null (vacio para onboarding hasta que se confirma el tenant)
  plan_id         = "uuid-plan"
  plan_cycle      = "month" | "year"
  amount          = "5.99"
  currency        = "USD"
  status          = "CREATED" | "PENDING" | "PAID" | "REJECTED" | "CANCELLED" | "FAILED"
  created_at      = ISO8601

Payment PAID (campos adicionales):
  confirmed_at  = ISO8601
  payer_id      = "user-id"
  payer_email   = "buyer@example.com"

Payment linkeado (tras onboarding o renovacion):
  tenant_id     = "tenant-real-uuid"   ← se fija atomicamente con repo.commit()
```

GSI `tenant-payments-index`: PK=`tenant_id`, SK=`created_at`. Para historial por tenant.

## Errores De Dominio

| Clase | Base | HTTP | Cuando |
| --- | --- | --- | --- |
| `FreePlanPaymentError` | `BusinessError` | 422 | Plan con precio 0 |
| `PlanNotFoundForPaymentError` | `NotFoundError` | 404 | Plan no existe |
| `PaymentNotFoundError` | `NotFoundError` | 404 | Orden no registrada |
| `PaymentAlreadyConfirmedError` | `AppError` | 409 | Orden ya confirmada (PAID) |
| `PaymentCreationError` | `AppError` | 502 | dLocal rechaza create |
| `PaymentConfirmError` | `AppError` | 502 | dLocal rechaza confirm o status no-PAID |

Nota: `BusinessError` → HTTP 422 (no 400). Ver `BACKEND.md` para la jerarquia de errores.

## Campos De Suscripcion En Tenant

```python
dlocal_payer_id                     str | None  — payer_id de la ultima confirmacion
subscription_status                 str | None  — "active" | "expired" | "none" | "pending_payment"
plan_cycle_ends_at                  str | None  — ISO8601 UTC; None cuando pending_payment
subscription_renewal_reminder_sent_at  str | None  — idempotencia del worker diario
```

`subscription_status` es gestionado por nuestra logica (no por dLocal).

`activate_subscription(payer_id, plan_cycle, now, updated_by)` — primera activacion:
setea `plan_cycle_ends_at = now + ciclo` (base siempre es `now`, el ciclo arranca al
pagar), `subscription_status="active"`, `dlocal_payer_id`. Opuesto a `apply_subscription_renewal`
que usa `max(now, plan_cycle_ends_at)` para no perder dias del ciclo anterior.

`apply_subscription_renewal(plan_cycle)` — renovacion: extiende `plan_cycle_ends_at`
desde `max(now, plan_cycle_ends_at)`, setea `subscription_status="active"` y limpia
`subscription_renewal_reminder_sent_at`.

`expire_subscription()` setea `subscription_status="expired"`.

## Tareas Manuales/Operativas Por Entorno

Antes de activar el pago en cada entorno:

1. Crear secret en Secrets Manager:
   ```
   aws secretsmanager create-secret \
     --name "codelabs-billing-{env}/dlocalgo-credentials" \
     --secret-string '{"api_key":"...","secret_key":"..."}' \
     --profile codelabs --region sa-east-1
   ```
2. Para sandbox: usar credenciales del sandbox de dLocal Go.
3. Para prod: usar credenciales de produccion.
4. Configurar `EXPO_PUBLIC_DLOCALGO_SMARTFIELDS_KEY` en el build del frontend
   (clave SmartFields, diferente de api_key/secret_key — solicitarla a soporte dLocal).
   En GitHub Actions vive como secret del environment (`dev`, `staging`, `prod`) y se inyecta
   en el step de build web.

## Frontend — Subscriptions

`frontend/features/subscriptions/`:
- `schemas.ts` — `createPaymentResultSchema`, `confirmPaymentResultSchema`,
  `paymentStatusSchema`, `applyRenewalResultSchema`
- `api.ts` — `subscriptionsApi.{createPayment, confirmPayment, getPayment, activateSubscription, applyRenewal}`
  `confirmPayment` recibe `{ card_token, client_first_name, client_last_name, client_email,
  client_document_type, client_document }`.
  `activateSubscription(tenantId, orderId, idempotencyKey)` llama `POST /tenants/{id}/subscription/activate`.
- `dlocal-types.ts` — interfaces TypeScript del SDK dLocal Go: `DLocalGoInstance`,
  `DLocalGoField`, `DLocalCardFieldOptions`; `declare global { Window.dlocalGo }`.
- `dlocal-field-options.ts` — estilos del campo SmartFields adaptados al tema activo.
- `use-dlocal-smartfields.ts` — hook React que encapsula carga del SDK, inicializacion,
  mount/unmount y estados `sdkReady`/`sdkError`. StrictMode-safe con flag `cancelled`.

SmartFields SDK:
- Sandbox: `https://checkout-sbx.dlocalgo.com/js/dlocalgo-smartfields-bundled.js`
- Produccion: `https://checkout.dlocalgo.com/js/dlocalgo-smartfields-bundled.js`
Seleccion via `config.env === 'prod'` en `constants/config.ts`.

El SDK se carga dinamicamente (`Platform.OS === 'web'` check) via `document.createElement('script')`.
En nativo (iOS/Android) se muestra un mensaje de "solo disponible en web".

### Formulario De Pago (ambas pantallas)

El pagador ingresa manualmente todos sus datos — no se infieren del perfil del tenant
(quien paga puede ser el contador con su tarjeta personal):

| Campo UI | Estado React | Enviado como |
| --- | --- | --- |
| Campo de tarjeta (SDK iframe) | ref SDK | `card_token` via `createCardToken` |
| Nombre | `firstName` | `client_first_name` |
| Apellido | `lastName` | `client_last_name` |
| Email | `payerEmail` | `client_email` |
| Tipo de documento (CI / RUC) | `documentType` | `client_document_type` |
| Numero de documento | `payerDocument` | `client_document` |

El boton de pago queda deshabilitado (opaco) hasta que el SDK este listo y todos los
campos esten completos.

### Pantallas

- Activacion (primera sesion): `frontend/features/subscriptions/screens/ActivateSubscriptionScreen.tsx`
  Ruta: `/(app)/activate-subscription` — fuera de `(tenant)/` para evitar loop del guard.
  Guard: `(tenant)/_layout.tsx` detecta `subscription_status === 'pending_payment'` y redirige aqui.
  Flujo: `useTenant` carga plan_id → `createPayment` → SDK SmartFields → formulario pagador
         → `confirmPayment` → `activateSubscription` → redirect dashboard.
- Billing (renovacion): `frontend/features/tenants/screens/BillingScreen.tsx`
  Flujo: "Pagar con tarjeta" → `createPayment` → SDK SmartFields → formulario pagador → `confirmPayment` → `applyRenewal`

## Worker Diario — subscription_renewal_notifier

Lambda disparada por EventBridge `cron(0 10 * * ? *)` (10:00 UTC).
Escanea tenants activos con `plan_cycle_ends_at <= now + 7 dias`.

## Deuda Tecnica

- `list_with_subscription_expiry_due` en `DynamoTenantRepository` usa scan — aceptable
  hasta ~10 K tenants activos; convertir en GSI cuando la cardinalidad lo requiera.
- Webhook dLocal no tiene retry/dead-letter: si el handler falla, dLocal reintentara
  segun su politica de reintentos pero no hay DLQ ni alerta para detectar perdida de eventos.
- 3DS no tiene timeout de sesion: si el usuario cierra la pestana sin completar la
  verificacion, el order queda `PENDING` en DynamoDB indefinidamente sin limpieza automatica.

## Deuda Solventada

- 2026-06-16: confirm payload corregido a campos flat `clientFirstName/LastName/Email/
  DocumentType/Document` (camelCase para dLocal) — eliminaba error 908 "Missing fields".
  El cuerpo anterior enviaba objeto `payer` anidado que dLocal rechazaba silenciosamente.
- 2026-06-16: datos del pagador separados del perfil del tenant: se ingresan manualmente
  en el formulario (el pagador puede ser el contador con su propia tarjeta/cedula).
- 2026-06-16: nombre del titular dividido en Nombre + Apellido; selector explícito CI/RUC;
  boton deshabilitado hasta completar todos los campos (opacidad 0.45 via prop `disabled`).
