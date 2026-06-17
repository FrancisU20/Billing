# Subscriptions — Dominio

Estado: **implementado Fase 3** — dLocal Go SmartFields (create + confirm + status),
wiring onboarding con pago obligatorio, endpoint de renovacion, worker diario de
vencimiento y pagina de billing en frontend.
Pendiente: checkout de renovacion por email (Fase 4 — link de pago en email) y
webhooks dLocal.

## Lee Tambien Antes De Empezar

Leer estos archivos en orden antes de escribir codigo en este dominio:

| Archivo | Por que |
| --- | --- |
| `CLAUDE.md` | Reglas no negociables (seguridad, git) |
| `BACKEND.md` | Patron `public_lambda_handler`, `get_secret_json`, Secrets Manager |
| `TENANTS.md` | Campos `dlocal_payer_id`, `subscription_status` en Tenant |
| `ONBOARDING.md` | El pago ocurre antes de crear el tenant (onboarding publico); `IPaymentVerifier` |

## Proposito

dLocal Go actua como pasarela de pago unico por ciclo de facturacion SaaS.
Se usa **SmartFields / Transparent Checkout** — formulario de tarjeta embebido en
la web, sin redireccion. El card token se genera en el browser via el SDK JS de
dLocal; nunca pasa por nuestros servidores (PCI DSS).

Distinto del dominio `INVOICES.md`, que sera la facturacion SRI que el tenant
emite a sus propios clientes.

## Flujo De Pago — Onboarding (plan de pago)

```
Frontend (wizard)        Backend                  dLocal Go
   |                       |                        |
   | [OTP correcto]         |                        |
   | navega a payment.tsx   |                        |
   |-- POST /subscriptions/payments (plan_id) ------>|
   |                   crea payment con allow_transparent=true |
   |<-- { order_id, checkout_token, amount, currency }
   |                       |                        |
   | SDK dLocal SmartFields (checkout_token)        |
   | payer ingresa tarjeta                          |
   | SDK -> card_token                              |
   |-- POST /subscriptions/payments/{order_id}/confirm
   |        { card_token }                  ------->|
   |<-- { status: "PAID", payer_id, ... }           |
   |                       |                        |
   |-- POST /onboarding/otp/confirm (con order_id)  |
   |         verifica pago PAID en tabla            |
   |         crea Tenant con subscription activa    |
   |<-- { success: true, tenant_id }                |
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
   |        { card_token }                  ------->|
   |<-- { status: "PAID" }                          |
   |-- POST /tenants/{id}/subscription/renew         |
   |         marca pago aplicado (tenant_id fijo)    |
   |         extiende plan_cycle_ends_at             |
   |<-- { plan_cycle_ends_at, subscription_status }  |
```

Planes gratuitos (`monthly_price == 0 && annual_price == 0`) no activan la
pasarela — `CreatePaymentUseCase` lanza `FreePlanPaymentError` (422).
En onboarding, planes gratuitos saltan el paso `payment.tsx` y van directo a
`/onboarding/otp/confirm` sin `order_id`.

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

# Renovacion vive en tenants/ (endpoint autenticado):
backend/lambdas/tenants/
  domain/
    commands.py          ApplySubscriptionRenewalCommand (+ existing)
    errors.py            PaymentNotCapturedError, PaymentAlreadyAppliedError, ... (+ existing)
    repositories/
      i_payment_verifier.py   IPaymentVerifier (ABC) — lectura de Payment desde onboarding domain
  use_cases/
    apply_subscription_renewal.py  ApplySubscriptionRenewalUseCase
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
{ "card_token": "tok_xxx", "payer_email": "buyer@example.com" }
```

Response 200:
```json
{ "data": { "order_id": "DP-12345", "status": "PAID", "payer_id": "...", "payer_email": "..." } }
```

Errores: 404 `PAYMENT_NOT_FOUND`, 409 `PAYMENT_ALREADY_CONFIRMED`, 502 `PAYMENT_CONFIRM_FAILED`.

Si dLocal retorna `REJECTED` u otro status no-PAID, el pago queda en `FAILED` y se lanza 502.
Si dLocal requiere 3DS, el flujo no esta implementado aun (Deuda Tecnica).

### GET /subscriptions/payments/{order_id}

Response 200:
```json
{ "data": { "order_id": "DP-12345", "status": "CREATED|PAID|FAILED|PENDING",
            "plan_id": "...", "plan_cycle": "month|year", "amount": "5.99", "currency": "USD",
            "tenant_id": null, "created_at": "...", "confirmed_at": "..." } }
```

Errores: 404 `PAYMENT_NOT_FOUND`.

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
subscription_status                 str | None  — "active" | "expired" | "none"
plan_cycle_ends_at                  str | None  — ISO8601 UTC; vencimiento del ciclo actual
subscription_renewal_reminder_sent_at  str | None  — idempotencia del worker diario
```

`subscription_status` es gestionado por nuestra logica (no por dLocal).
`apply_subscription_renewal(plan_cycle)` extiende `plan_cycle_ends_at` en 1 mes o 1 anio,
setea `subscription_status="active"` y limpia `subscription_renewal_reminder_sent_at`.
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
- `api.ts` — `subscriptionsApi.{createPayment, confirmPayment, getPayment, applyRenewal}`

SmartFields SDK:
- Sandbox: `https://checkout-sbx.dlocalgo.com/js/dlocalgo-smartfields-bundled.js`
- Produccion: `https://checkout.dlocalgo.com/js/dlocalgo-smartfields-bundled.js`
Seleccion via `config.env === 'prod'` en `constants/config.ts`.

El SDK se carga dinamicamente (`Platform.OS === 'web'` check) vía `document.createElement('script')`.
En nativo (iOS/Android) se muestra un mensaje de "solo disponible en web".

Pantalla de billing: `frontend/features/tenants/screens/BillingScreen.tsx`
Flujo: "Pagar con tarjeta" → `createPayment` → SDK SmartFields → `confirmPayment` → `applyRenewal`

## Worker Diario — subscription_renewal_notifier

Lambda disparada por EventBridge `cron(0 10 * * ? *)` (10:00 UTC).
Escanea tenants activos con `plan_cycle_ends_at <= now + 7 dias`.

## Deuda Tecnica

- Checkout de renovacion por email (Fase 4): el worker notifica pero no genera link de pago.
- Sin webhooks dLocal: no detectamos cambios de estado asincronos desde dLocal.
- Sin manejo de 3DS: si dLocal requiere autenticacion 3DS, el confirm retorna `redirect_url`
  pero el frontend no lo gestiona aun. A implementar cuando sea necesario.
- `list_with_subscription_expiry_due` en `DynamoTenantRepository` usa scan — aceptable
  con poco volumen; convertir en GSI cuando la cardinalidad lo requiera.
