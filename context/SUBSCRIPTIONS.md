# Subscriptions — Dominio

Estado: **implementado Fase 3** — PayPal Orders API (create + capture + status), wiring
onboarding con pago obligatorio, endpoint de renovacion, worker diario de vencimiento y
pagina de billing en frontend.
Pendiente: renovacion automatica por email (Fase 4 — checkout via link en email) y
webhooks PayPal.

## Lee Tambien Antes De Empezar

Leer estos archivos en orden antes de escribir codigo en este dominio:

| Archivo | Por que |
| --- | --- |
| `CLAUDE.md` | Reglas no negociables (seguridad, git) |
| `BACKEND.md` | Patron `public_lambda_handler`, `get_secret_json`, Secrets Manager |
| `TENANTS.md` | Campos `paypal_payer_id`, `subscription_status` en Tenant |
| `ONBOARDING.md` | El pago ocurre antes de crear el tenant (onboarding publico); `IPaymentVerifier` |

## Proposito

PayPal actua como pasarela de pago unico por ciclo de facturacion SaaS.
**No se usa PayPal Subscriptions** — se crea una orden (`CAPTURE`) por periodo
y el tenant aprueba manualmente cada pago (estilo Netflix cuando falla tarjeta).

Distinto del dominio `INVOICES.md`, que sera la facturacion SRI que el tenant
emite a sus propios clientes.

## Flujo De Pago — Onboarding (plan de pago)

```
Frontend (wizard)        Backend                  PayPal
   |                       |                        |
   | [OTP correcto]         |                        |
   | navega a payment.tsx   |                        |
   |-- POST /subscriptions/payments (plan_id) ------>|
   |                   crea orden                   |
   |<-- { order_id, amount, currency }              |
   |                       |                        |
   | Linking.openURL(paypalApprovalUrl)             |
   |<-- payer aprueba en navegador del sistema -----|
   |                       |                        |
   |-- GET /subscriptions/payments/{order_id}       |
   |<-- { status: "APPROVED" }                      |
   |-- POST /subscriptions/payments/{order_id}/capture
   |<-- { status: "CAPTURED", payer_id, ... }       |
   |                       |                        |
   |-- POST /onboarding/otp/confirm (con order_id)  |
   |         verifica pago CAPTURED en tabla        |
   |         crea Tenant con subscription activa    |
   |<-- { success: true, tenant_id }                |
```

## Flujo De Renovacion — Billing

```
Frontend (billing.tsx)   Backend                  PayPal
   |                       |                        |
   |-- POST /subscriptions/payments (plan_id) ------>|
   |<-- { order_id, amount }                         |
   | Linking.openURL(paypalApprovalUrl)              |
   |<-- payer aprueba ------------------------------|
   |-- GET /subscriptions/payments/{order_id}        |
   |<-- { status: "APPROVED" }                       |
   |-- POST /subscriptions/payments/{order_id}/capture
   |<-- { status: "CAPTURED" }                       |
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
    commands.py          CreatePaymentCommand, CapturePaymentCommand, GetPaymentStatusCommand
    errors.py            FreePlanPaymentError, PaymentNotFoundError, ...
    interfaces/
      i_paypal_client.py IPayPalClient (ABC), PayPalOrderResult, PayPalCaptureResult
    entities/
      payment.py         Payment (order_id, tenant_id, plan_id, plan_cycle, amount, status, ...)
    repositories/
      i_payment_repository.py  get_by_order_id(), mark_applied_to_tenant()
      i_plan_catalog.py  PlanSummary (monthly_price, annual_price, limit_cycle, is_free)
  infra/
    paypal_client.py     PayPalClient(IPayPalClient): OAuth2 (cache de token en modulo)
    payment_repository.py  DynamoDB (PK = "PAYMENT#{order_id}")
    plan_catalog.py      Lectura local de planes sin importar lambdas.plans.*
  use_cases/
    create_payment.py    CreatePaymentUseCase
    capture_payment.py   CapturePaymentUseCase
    get_payment_status.py GetPaymentStatusUseCase
  schemas.py             CreatePaymentRequest
  handler.py             POST /subscriptions/payments
                         POST /subscriptions/payments/{order_id}/capture
                         GET  /subscriptions/payments/{order_id}

# Renovacion vive en tenants/ (endpoint autenticado):
backend/lambdas/tenants/
  domain/
    commands.py          ApplySubscriptionRenewalCommand (+ existing)
    errors.py            OnboardingPaymentRequiredError, PaymentNotCapturedError,
                         PaymentAlreadyAppliedError, PaymentPlanMismatchError (+ existing)
    repositories/
      i_payment_verifier.py   IPaymentVerifier (ABC) — lectura de Payment desde onboarding domain
  use_cases/
    apply_subscription_renewal.py  ApplySubscriptionRenewalUseCase
  infra/
    payment_verifier.py    PaymentVerifier(IPaymentVerifier): lee tabla payments

# Worker diario:
backend/lambdas/workers/subscription_renewal_notifier/
  handler.py             EventBridge cron(0 10 * * ? *)
  use_case.py            NotifySubscriptionRenewalUseCase
                         — expired: expire_subscription() + send_subscription_expired email
                         — within 7 days + reminder_not_sent: marca reminder + envia email
```

## Componentes Externos

- Lambda: `backend/lambdas/subscriptions/`
- DynamoDB: tabla `payments` (PK=`id` = `"PAYMENT#{order_id}"`, GSI `tenant-payments-index`)
- Secrets Manager: `codelabs-billing-{env}/paypal-credentials`
  JSON con `{"client_id": "...", "secret": "..."}` — creado manualmente por entorno

## Configuracion

| Variable de entorno | Valor dev/staging | Valor prod |
| --- | --- | --- |
| `PAYMENTS_TABLE` | (del stack) | (del stack) |
| `PLANS_TABLE` | (del stack) | (del stack) |
| `PAYPAL_CREDENTIALS_NAME` | `codelabs-billing-dev/paypal-credentials` | `codelabs-billing-prod/paypal-credentials` |
| `PAYPAL_API_URL` | `https://api-m.sandbox.paypal.com` | `https://api-m.paypal.com` |

## API Contract

| Metodo | Ruta | Auth | Descripcion |
| --- | --- | --- | --- |
| POST | `/subscriptions/payments` | ninguna (publico) | Crea orden PayPal y registra Payment |
| POST | `/subscriptions/payments/{order_id}/capture` | ninguna (publico) | Captura pago |
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
{ "data": { "order_id": "ORDER-ID", "amount": "5.99", "currency": "USD" } }
```

Errores: 422 `FREE_PLAN_NO_PAYMENT`, 404 `PLAN_NOT_FOUND`, 502 `PAYMENT_CREATION_FAILED`.

### POST /subscriptions/payments/{order_id}/capture

Response 200:
```json
{ "data": { "order_id": "...", "status": "CAPTURED", "payer_id": "...", "payer_email": "..." } }
```

Errores: 404 `PAYMENT_NOT_FOUND`, 409 `PAYMENT_ALREADY_CAPTURED`, 502 `PAYMENT_CAPTURE_FAILED`.

### GET /subscriptions/payments/{order_id}

Response 200:
```json
{ "data": { "id": "PAYMENT#...", "order_id": "...", "status": "APPROVED|CAPTURED|CREATED|FAILED",
            "plan_id": "...", "plan_cycle": "month|year", "amount": "5.99", "currency": "USD",
            "tenant_id": "", "created_at": "...", "updated_at": "..." } }
```

Errores: 404 `PAYMENT_NOT_FOUND`.

### POST /tenants/{id}/subscription/renew

Requiere `X-Idempotency-Key`.

Request:
```json
{ "order_id": "ORDER-ID" }
```

Response 200:
```json
{ "data": { "tenant_id": "...", "plan_cycle_ends_at": "...", "subscription_status": "active" } }
```

Guards (todos 422 BusinessError):
- `PAYMENT_NOT_CAPTURED` — pago no esta en estado CAPTURED
- `PAYMENT_ALREADY_APPLIED` — pago ya fue aplicado a un tenant
- `PAYMENT_PLAN_MISMATCH` — el plan_id del pago no coincide con el plan activo del tenant

El endpoint llama a `tenant.apply_subscription_renewal(plan_cycle)` que extiende
`plan_cycle_ends_at` por 1 mes o 1 anio segun `plan_cycle` del pago y setea
`subscription_status = "active"` y limpia `subscription_renewal_reminder_sent_at`.
La marcacion del pago como aplicado (`mark_applied_to_tenant`) es atomica via
`extra_transact_items` en el mismo `repo.commit()`.

## DynamoDB Schema

Tabla: `payments`. PK = `id` (sin SK).

```
Payment CREATED:
  id            = "PAYMENT#{order_id}"
  order_id      = "ORDER-ID"
  tenant_id     = ""  (vacio para onboarding hasta que se confirma el tenant)
                  o   tenant_id real si es renovacion posterior
  plan_id       = "uuid-plan"
  plan_cycle    = "month" | "year"   ← nuevo (S8)
  amount        = "5.99"
  currency      = "USD"
  status        = "CREATED" | "CAPTURED" | "FAILED"
  created_at    = ISO8601
  updated_at    = ISO8601

Payment CAPTURED (campos adicionales):
  captured_at   = ISO8601
  payer_id      = "PAYER-ID"
  payer_email   = "buyer@example.com"

Payment APPLIED (tras renovacion o confirmacion de onboarding):
  tenant_id     = "tenant-real-uuid"   ← se fija atomicamente con repo.commit()
```

GSI `tenant-payments-index`: PK=`tenant_id`, SK=`created_at`. Disponible para
historial de pagos por tenant. En onboarding, `tenant_id=""` hasta que se confirma.

## Errores De Dominio

| Clase | Base | HTTP | Cuando |
| --- | --- | --- | --- |
| `FreePlanPaymentError` | `BusinessError` | 422 | Plan con precio 0 |
| `PlanNotFoundForPaymentError` | `NotFoundError` | 404 | Plan no existe |
| `PaymentNotFoundError` | `NotFoundError` | 404 | Orden no registrada |
| `PaymentAlreadyCapturedError` | `AppError` | 409 | Orden ya capturada |
| `PaymentCreationError` | `AppError` | 502 | PayPal rechaza create order |
| `PaymentCaptureError` | `AppError` | 502 | PayPal rechaza capture |
| `OnboardingPaymentRequiredError` | `BusinessError` | 422 | Plan de pago sin order_id en otp/confirm |
| `PaymentNotCapturedError` | `BusinessError` | 422 | Pago no en estado CAPTURED al renovar |
| `PaymentAlreadyAppliedError` | `BusinessError` | 422 | Pago ya fue aplicado a un tenant |
| `PaymentPlanMismatchError` | `BusinessError` | 422 | plan_id del pago difiere del plan del tenant |

Nota: `BusinessError` → HTTP 422 (no 400). Ver `BACKEND.md` para la jerarquia de errores.

## Campos De Suscripcion En Tenant

```python
paypal_payer_id                     str | None  — payer_id de la ultima captura
subscription_status                 str | None  — "active" | "expired" | "none"
plan_cycle_ends_at                  str | None  — ISO8601 UTC; vencimiento del ciclo actual
subscription_renewal_reminder_sent_at  str | None  — idempotencia del worker diario
```

`subscription_status` es gestionado por nuestra logica (no por PayPal).
`apply_subscription_renewal(plan_cycle)` extiende `plan_cycle_ends_at` en 1 mes o 1 anio,
setea `subscription_status="active"` y limpia `subscription_renewal_reminder_sent_at`.
`expire_subscription()` setea `subscription_status="expired"`.
`mark_renewal_reminder_sent()` pisa `subscription_renewal_reminder_sent_at=now`.

## Tareas Manuales/Operativas Por Entorno

Antes de activar el pago en cada entorno:

1. Crear secret en Secrets Manager:
   ```
   aws secretsmanager create-secret \
     --name "codelabs-billing-{env}/paypal-credentials" \
     --secret-string '{"client_id":"APP-XXX","secret":"YYY"}' \
     --profile codelabs --region sa-east-1
   ```
2. Para sandbox: usar credenciales de la sandbox app en el dashboard PayPal Developer.
3. Para prod: usar credenciales de la live app.

## Worker Diario — subscription_renewal_notifier

Lambda disparada por EventBridge `cron(0 10 * * ? *)` (10:00 UTC).
Escanea tenants activos con `plan_cycle_ends_at <= now + 7 dias`:

- Si `plan_cycle_ends_at <= now`: llama `tenant.expire_subscription()`, envia email
  `SubscriptionExpiredEvent`.
- Si `plan_cycle_ends_at <= now + 7 dias` y `subscription_renewal_reminder_sent_at` es None:
  llama `tenant.mark_renewal_reminder_sent()`, envia email `SubscriptionRenewalReminderEvent`.

Idempotencia: el flag `subscription_renewal_reminder_sent_at` impide repetir el reminder.
En expirations no hay flag porque el status `expired` ya es idempotente.

Emails nuevos en `email_notifications/`:
- `SubscriptionRenewalReminderEvent` — con `days_remaining` y `plan_cycle_ends_at`
- `SubscriptionExpiredEvent` — aviso de vencimiento

## Frontend — Subscriptions

`frontend/features/subscriptions/`:
- `schemas.ts` — `createPaymentResultSchema`, `capturePaymentResultSchema`,
  `paymentStatusSchema`, `applyRenewalResultSchema`
- `api.ts` — `subscriptionsApi.{createPayment, capturePayment, getPayment, applyRenewal, paypalApprovalUrl}`

URL de aprobacion PayPal:
- Sandbox: `https://www.sandbox.paypal.com/checkoutnow?token={order_id}`
- Produccion: `https://www.paypal.com/checkoutnow?token={order_id}`
Seleccion via `config.env === 'prod'`.

Pantalla de billing: `frontend/features/tenants/screens/BillingScreen.tsx`
Ruta: `frontend/app/(app)/(tenant)/billing.tsx` → `Routes.tenant.billing`
Nav item: "Facturación" con icono `card-outline` en el sidebar tenant.

Flujo en BillingScreen:
1. "Pagar con PayPal" → `createPayment` → `Linking.openURL(paypalApprovalUrl)` → `paypalOpened=true`
2. "Ya completé el pago en PayPal" → `getPayment` → si APPROVED: `capturePayment` → `applyRenewal` → refresh tenant

## Deuda Tecnica

- Renovacion automatica por email (Fase 4): el worker notifica pero el pago aun es manual.
  El ideal es enviar un link de checkout directo en el email de recordatorio.
- Sin webhooks PayPal: no detectamos pagos fuera del flujo normal (ej. PayPal cancela
  automaticamente). A implementar cuando el volumen lo justifique.
- `list_with_subscription_expiry_due` en `DynamoTenantRepository` usa scan con filtro —
  aceptable con poco volumen; a convertir en GSI (PK=`subscription_status`, SK=`plan_cycle_ends_at`)
  cuando la cardinalidad de tenants activos lo requiera.
- Sin reintentos ni alertas si la captura falla a medias.
