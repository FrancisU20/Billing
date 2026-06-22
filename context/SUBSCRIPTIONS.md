# Subscriptions — Dominio

Estado: **implementado completo** — dLocal Go SmartFields (create + confirm + status),
modelo Netflix (registro sin pago, activacion en primera sesion), endpoint de activacion
autenticado, endpoint de renovacion, worker diario de vencimiento con link `/billing` en
email, pagina de billing, webhook dLocal Go con HMAC-SHA256, endpoint de reembolso
(superadmin), manejo de 3DS en frontend (`use3dsFlow` hook), formulario de pago con datos
del pagador independiente del perfil del tenant, **resiliencia de 4 capas** en el flujo
de activacion/renovacion (retry, degradacion graceful, guard auto-activate, reconciliador
cada 5 min), **markup 12%** sobre el precio neto del plan, **cobro automatico** en
renovacion via `dlocal_payer_id` guardado, estado `payment_failed` con banner de accion
requerida y endpoint `retry-payment` para reintentar tarjeta guardada. Desde 2026-06-21,
pantalla de **confirmar/cambiar plan** post-registro antes de pagar (`PATCH /tenants/{id}/plan`).

## Lee Tambien Antes De Empezar

Leer estos archivos en orden antes de escribir codigo en este dominio:

| Archivo | Por que |
| --- | --- |
| `CLAUDE.md` | Reglas no negociables (seguridad, git) |
| `BACKEND.md` | Patron `public_lambda_handler`, `get_secret_json`, Secrets Manager |
| `TENANTS.md` | Campos `dlocal_payer_id`, `subscription_status`, `pending_order_id` en Tenant |
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

## Confirmar/Cambiar Plan Post-Registro

Agregado 2026-06-21. Entre el cambio de password forzado y el pago (o el dashboard, si
el plan es gratis) hay un paso intermedio para CUALQUIER tenant nuevo, gratis o de pago:
confirmar el plan elegido en el registro o cambiarlo. Ver `ONBOARDING.md` → "Flujo De
Registro" pasos 11-13 para donde encaja esto en la secuencia completa.

```
PATCH /tenants/{id}/plan          owner|admin|superadmin, idempotente
  Body: { plan_id }
  Solo si tenant.subscription_status in (None, 'pending_payment') — si no,
    TenantPlanChangeNotAllowedError (422): ya paso por aqui o ya esta activo.
  Solo si el plan destino es self_service=true — si no,
    TenantPlanNotSelfServiceError (422): Enterprise no se elige aqui.
  ChangePlanUseCase → Tenant.confirm_plan_selection(plan_id, plan_limit_cycle, plan_is_free, updated_by):
    - plan_id = nuevo
    - pending_order_id = None (invalida cualquier orden de pago anterior — el monto
      cambio si el plan cambio)
    - is_free:  subscription_status=None,            plan_cycle_ends_at = now + ciclo
    - !is_free: subscription_status='pending_payment', plan_cycle_ends_at = None
    - plan_confirmed_at = now()   ← esto es lo que saca al tenant de este paso
```

`IPlanCatalog.ensure_self_service_active(plan_id)` (en `lambdas/tenants/infra/plan_catalog.py`,
NO el `IPlanCatalog` del dominio `onboarding` — son interfaces distintas con el mismo
nombre, cada lambda tiene su propia copia para no acoplar bundles) hace el mismo `get_item`
que `ensure_active()` pero ademas valida `self_service` y devuelve si es gratis
(`monthly_price == 0 and annual_price == 0`, no es un campo persistido — ver `PLANS.md`).

Frontend: `ConfirmPlanScreen` (`/(app)/confirm-plan`, fuera del grupo `(tenant)` —
mismo motivo que `activate-subscription`: si estuviera dentro, el guard que redirige
aqui crearia un loop). Reusa `usePlans()` + `PlanCard` filtrando `self_service`, muestra
el plan actual resaltado, y SIEMPRE llama `tenantsApi.changePlan(...)` al confirmar
(incluso si el usuario no cambio nada) — es lo que setea `plan_confirmed_at` y saca al
tenant de este paso para siempre. Segun la respuesta:
- `subscription_status === 'pending_payment'` → `router.replace(activateSubscription)`
- si no → `router.replace(uploadCertificate)` (ver `CERTIFICATES.md`)

Guard en `(tenant)/_layout.tsx`, ANTES del guard de `pending_payment` (ver "Flujo De
Activacion" abajo):

```ts
const needsPlanConfirmation = !tenant?.plan_confirmed_at && !tenant?.cert_uploaded_at
if (needsPlanConfirmation) return <Redirect href={Routes.app.confirmPlan} />
```

El segundo termino (`!tenant?.cert_uploaded_at`) es deliberado: un tenant creado ANTES
de 2026-06-21 ya subio su certificado durante el wizard de registro (modelo viejo), asi
que `cert_uploaded_at` ya esta seteado y este guard nunca se activa para el — aunque
`plan_confirmed_at` sea `null` para siempre (no hay backfill, no hace falta).

## Flujo De Activacion — Primera Sesion (plan de pago)

```
Frontend (app autenticada)  Backend              dLocal Go
   |                          |                    |
   | login → JWT               |                    |
   | (tenant)/_layout.tsx      |                    |
   | needsPlanConfirmation?    |                    |
   |   → si SI: redirect confirm-plan (ver arriba) |
   | detecta pending_payment   |                    |
   |   + pending_order_id?     |                    |
   |   → si SI: banner auto-activate               |
   |   → si NO: redirect activate-sub             |
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
   |    [retry x3: 1s/2s/4s]                       |
   |    Phase 1: SET pending_order_id = order_id   |
   |    Phase 2: transact_write (activa tenant +   |
   |             linkea payment)                   |
   |<-- { plan_cycle_ends_at, subscription_status } |
   | → redirect dashboard (el guard intercepta y    |
   |   redirige a upload-certificate si             |
   |   !cert_uploaded_at — ver CERTIFICATES.md)     |
```

Si el `activate` falla despues de todas las retries:
- `pending_order_id` ya fue escrito en DynamoDB (Phase 1 se ejecuta antes del commit).
- En el mismo request o en la proxima carga, el guard detecta `pending_order_id` y muestra
  el dashboard con `PendingActivationBanner` que reintenta automaticamente.
- Si el browser se cierra, el reconciliador (EventBridge cada 5 min) activa al tenant.

## Flujo De Renovacion — Billing

```
Frontend (billing.tsx)   Backend                  dLocal Go
   |                       |                        |
   |-- POST /subscriptions/payments (plan_id) ------>|
   |<-- { order_id, checkout_token, amount }         |
   | SDK SmartFields (checkout_token)                |
   | payer ingresa tarjeta -> card_token             |
   |-- POST /subscriptions/payments/{order_id}/confirm
   |        { card_token, client_* }                |
   |<-- { status: "PAID" }                          |
   |-- POST /tenants/{id}/subscription/renew         |
   |    [retry x3: 1s/2s/4s]                       |
   |         extiende plan_cycle_ends_at            |
   |<-- { plan_cycle_ends_at, subscription_status }  |
```

Planes gratuitos (`monthly_price == 0 && annual_price == 0`) no activan la
pasarela — `CreatePaymentUseCase` lanza `FreePlanPaymentError` (422).
En el modelo Netflix, tenants con plan gratuito no tienen `subscription_status='pending_payment'`
y pasan directo al dashboard sin pantalla de activacion.

## Markup De Procesamiento (12%)

Todo pago de suscripcion incluye un 12% de comision fija. El precio neto queda en el plan;
el cliente paga el precio gross.

```python
# backend/shared/billing.py
MARKUP_PCT = Decimal("0.12")

def gross_price(net: str) -> str:
    # ej. "5.99" -> "6.71"
    return f"{(Decimal(net) * (1 + MARKUP_PCT)).quantize(Decimal('0.01'), ROUND_HALF_UP):.2f}"
```

El endpoint `POST /subscriptions/payments` ahora devuelve tres campos de precio:

```json
{ "amount": "6.71", "net_amount": "5.99", "markup_pct": "12", "currency": "USD" }
```

- `amount` = precio gross cobrado a dLocal (lo que se debita de la tarjeta).
- `net_amount` = precio base del plan (sin markup).
- `markup_pct` = porcentaje de comision como string entero.

`RetryPaymentUseCase` y el cobro automatico del worker usan `gross_price()` de la misma
funcion para garantizar coherencia. El markup se aplica igual para ciclo mensual y anual.

## Cobro Automatico En Renovacion

El worker diario `subscription_renewal_notifier` extiende su logica cuando el tenant tiene
`dlocal_payer_id` guardado de un pago anterior:

```
tenant vencido + dlocal_payer_id SET
  → POST /v1/payments { payer: { id: payer_id }, amount: gross_price(plan), ... }
  → PAID  → payment.save() + apply_subscription_renewal() + repo.save(tenant)
  → FAILED / REJECTED → tenant.mark_payment_failed() + repo.save() + send_payment_failed email

tenant vencido + sin dlocal_payer_id
  → expire_subscription() + send_subscription_expired email (flujo anterior)
```

`mark_payment_failed()` setea `subscription_status = "payment_failed"`. El tenant sigue
activo en la plataforma pero ve el `PaymentFailedBanner` en cada pantalla.

El cobro automatico requiere que el worker tenga configurados `PLANS_TABLE`,
`PAYMENTS_TABLE` y `DLOCALGO_CREDENTIALS_NAME`. Si alguno falta, el worker cae al
comportamiento anterior (solo notificacion/expiracion), sin auto-charge.

**Grace period para `payment_failed`**: si el primer cobro automatico falla, el tenant
queda en `payment_failed` y el worker reintenta diariamente durante 7 dias
(`_PAYMENT_FAILED_GRACE_DAYS = 7`) contados desde `plan_cycle_ends_at`. Al superar la
gracia (o si no hay `dlocal_payer_id`), la suscripcion se expira y se envia el email de
expiracion. El email de pago fallido solo se envia **una vez** (en el primer fallo);
los reintentos siguientes no reenvian el email aunque fallen.

## Estado payment_failed

`subscription_status = "payment_failed"` indica que el cobro automatico fallo. El tenant:
- Puede seguir navegando el dashboard (no se bloquea la sesion).
- Ve `PaymentFailedBanner` encima del Stack en toda la app (`(tenant)/_layout.tsx`).
- El banner intenta `POST /tenants/{id}/subscription/retry-payment` automaticamente al montar.
  - Si tiene exito → `refresh()` del tenant → banner desaparece.
  - Si falla → muestra dos botones: "Reintentar tarjeta guardada" y "Pagar con tarjeta nueva".
- "Pagar con tarjeta nueva" navega a `/billing` donde `BillingScreen` adapta su UI para
  `payment_failed` y permite pagar con SmartFields → `POST /tenants/{id}/subscription/renew`.

Transiciones desde `payment_failed`:
```
payment_failed ──► active   (via retry-payment exitoso o renew exitoso con nueva tarjeta)
payment_failed ──► expired  (si el worker diario vuelve a correr y no tiene payer_id)
```

## Resiliencia De Pago — 4 Capas

El flujo de pago puede fallar despues de que dLocal confirma PAID (fallo de red en
`activate` o `renew`). La arquitectura tiene 4 capas de recuperacion:

### Capa 1 — Retry con backoff exponencial (frontend)

`retryWithBackoff(fn, [1000, 2000, 4000])` en `lib/utils/retry.ts`.
Envuelve la llamada a `activateSubscription` (en `ActivateSubscriptionScreen`)
y `applyRenewal` (en `BillingScreen`), incluyendo el path post-3DS.
Cubre fallos transitorios de red o cold start de Lambda.

### Capa 2 — `pending_order_id` como bookmark (backend, Phase 1)

En `ActivateSubscriptionUseCase.execute()`, **antes** del `transact_write` principal:
```python
self._tenant_repo.set_pending_order_id(tenant_id, order_id)
# ↑ DynamoDB update_item condicional: solo si subscription_status='pending_payment'
# Sobrevive si el commit falla. Se limpia cuando activate_subscription() en el
# domain model setea self.pending_order_id = None (incluido en el transact_write exitoso).
```

Si el commit falla, el tenant queda con `subscription_status='pending_payment'` +
`pending_order_id='DP-xxx'`. Ese estado es la señal para las capas 3 y 4.

### Capa 3 — Guard auto-activate (frontend)

`(tenant)/_layout.tsx` revisa al cargar el tenant:

```
pending_payment + pending_order_id SET  → muestra dashboard + PendingActivationBanner
pending_payment + pending_order_id NULL → redirect a ActivateSubscriptionScreen
activo/expirado                         → pass-through normal
```

`PendingActivationBanner` auto-llama `activateSubscription` (con retry) al montar.
Si tiene exito llama `refresh()` del `useTenant` hook, que recarga el tenant y
elimina el banner. Si falla muestra boton "Reintentar".

### Capa 4 — Reconciliador (worker EventBridge cada 5 min)

`backend/lambdas/workers/pending_activation_reconciler/`
- Disparado por `rate(5 minutes)`.
- Escanea tenants con `subscription_status='pending_payment'` + `pending_order_id` seteado.
- Para cada uno ejecuta `ActivateSubscriptionUseCase` + `repo.commit()`.
- Errores de dominio conocidos (ya activo, plan mismatch, pago no confirmado) → skip.
- Errores inesperados → log + contador `errors` en el resultado.
- Cubre el caso extremo: browser cerrado, localStorage limpiado, usuario en otro dispositivo.

## Arquitectura

```
subscriptions/
  domain/
    commands.py          CreatePaymentCommand, ConfirmPaymentCommand
    errors.py            FreePlanPaymentError, PaymentNotFoundError, ...
    repositories/
      i_dlocal_client.py IDLocalClient (ABC): create_payment, confirm_payment, charge_saved_payer,
                         refund_payment. Results: DLocalCreatePaymentResult,
                         DLocalConfirmPaymentResult, DLocalDirectChargeResult
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
    create_payment.py    CreatePaymentUseCase
    confirm_payment.py   ConfirmPaymentUseCase
    get_payment.py       GetPaymentUseCase
  handler.py             POST /subscriptions/payments
                         POST /subscriptions/payments/{order_id}/confirm
                         GET  /subscriptions/payments/{order_id}
                         POST /subscriptions/payments/{order_id}/refund
                         POST /subscriptions/webhooks/dlocal

# Activacion y Renovacion viven en tenants/ (endpoints autenticados):
backend/lambdas/tenants/
  domain/
    repositories/
      i_payment_reader.py     IPaymentReader (ABC) — lectura y mark_applied de Payment
  use_cases/
    activate_subscription.py  ActivateSubscriptionUseCase — Phase1 (set_pending_order_id)
                               + Phase2 (transact_write activacion + linkeo payment)
    apply_subscription_renewal.py  ApplySubscriptionRenewalUseCase — acepta cualquier
                               subscription_status; solo valida que el pago este PAID
    retry_payment.py      RetryPaymentUseCase — cobra via dlocal_payer_id guardado;
                          elegible en status "payment_failed" | "expired"; 402 si rechazado
  infra/
    payment_reader.py    DynamoPaymentReader

# Workers:
backend/lambdas/workers/subscription_renewal_notifier/
  handler.py             EventBridge cron(0 10 * * ? *) — recordatorio/vencimiento diario
  use_case.py            NotifySubscriptionRenewalUseCase

backend/lambdas/workers/pending_activation_reconciler/
  handler.py             EventBridge rate(5 minutes) — activa tenants con pending_order_id
  use_case.py            PendingActivationReconcilerUseCase

# Frontend:
frontend/lib/utils/retry.ts                                   retryWithBackoff()
frontend/features/subscriptions/components/PendingActivationBanner.tsx
frontend/app/(app)/(tenant)/_layout.tsx                       guard con auto-activate
frontend/features/subscriptions/screens/ActivateSubscriptionScreen.tsx
frontend/features/tenants/screens/BillingScreen.tsx
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
| POST | `/subscriptions/webhooks/dlocal` | HMAC-SHA256 (sin JWT) | Recibe notificaciones asincronas de dLocal Go |
| POST | `/tenants/{id}/subscription/activate` | JWT (tenant owner/admin) | Activa suscripcion pending_payment |
| POST | `/tenants/{id}/subscription/renew` | JWT (tenant owner/admin) | Aplica renovacion de ciclo |
| POST | `/tenants/{id}/subscription/retry-payment` | JWT (tenant owner/admin) | Reintenta cobro con tarjeta guardada |

### POST /subscriptions/payments

Requiere `X-Idempotency-Key` (ver `BACKEND.md`).

Request:
```json
{ "plan_id": "uuid-plan", "currency": "USD" }
```

Response 201:
```json
{
  "data": {
    "order_id": "DP-12345",
    "checkout_token": "mct_xxx",
    "amount": "6.71",
    "net_amount": "5.99",
    "markup_pct": "12",
    "currency": "USD"
  }
}
```

`amount` es el valor gross cobrado a dLocal. `net_amount` es el precio base del plan.
El frontend muestra el desglose via `PriceBreakdown`.

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

409 se retorna si el pago ya tiene status `PAID`, `AUTHORIZED` o `PENDING`. El estado `PENDING`
bloquea re-confirmacion porque el proceso 3DS ya esta en vuelo — la resolucion llega via webhook,
no via un segundo confirm.

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
Eventos con `type != "PAYMENT"`, sin `order_id`, o con `status` vacio se responden 200 sin
procesar (se loguea warning si falta `order_id`). No se usa ningun campo alternativo como
fallback: `order_id` es obligatorio en el payload de dLocal.
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

### POST /tenants/{id}/subscription/retry-payment

Requiere `X-Idempotency-Key`. Cobra con el `dlocal_payer_id` guardado del tenant.
Solo elegible si `subscription_status` es `"payment_failed"` o `"expired"`.

Request: sin body (los datos del pago se derivan del tenant).

Response 200:
```json
{ "data": { "tenant_id": "...", "plan_cycle_ends_at": "...", "subscription_status": "active" } }
```

Errores:
- 422 `NO_SAVED_PAYMENT_METHOD` — el tenant nunca confirmo un pago con SmartFields.
- 402 `SAVED_CARD_REJECTED` — dLocal rechazo el cobro o fallo la llamada HTTP.
- 422 `RETRY_PAYMENT_NOT_ELIGIBLE` — el status no es `payment_failed` ni `expired`.

**Garantia transaccional**: Payment y Tenant se escriben en el mismo `transact_write`
via `save_transact_item()`. Si el commit del Tenant falla, el Payment tampoco queda
escrito — no hay riesgo de pagos huerfanos por este path.

### PATCH /tenants/{id}/plan

Ver "Confirmar/Cambiar Plan Post-Registro" arriba. Requiere `X-Idempotency-Key`.

Request:
```json
{ "plan_id": "uuid-plan" }
```

Response 200: el `Tenant` completo (`tenant.to_dict()`), igual que `PATCH /tenants/{id}`.

Errores: 422 `TENANT_PLAN_CHANGE_NOT_ALLOWED` (subscription_status fuera de
`None`/`pending_payment`), 422 `TENANT_PLAN_NOT_SELF_SERVICE` (plan destino Enterprise).

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
  status          = "CREATED" | "PENDING" | "PAID" | "REJECTED" | "CANCELLED" | "FAILED" | "REFUNDED"
  created_at      = ISO8601

Payment PAID (campos adicionales):
  confirmed_at  = ISO8601
  payer_id      = "user-id"
  payer_email   = "buyer@example.com"

Payment PENDING o FAILED (campos adicionales):
  error_detail  = "dLocal error: ..." | "dLocal requires customer action" | null

Payment REFUNDED (campos adicionales):
  status        = "REFUNDED"   ← set por refund_payment use case

Payment linkeado (tras activate o renovacion):
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
| `NoSavedPaymentMethodError` | `BusinessError` | 422 | Tenant sin `dlocal_payer_id` en retry-payment |
| `SavedCardRejectedError` | `AppError` | **402** | dLocal rechaza cobro automatico o retry |
| `RetryPaymentNotEligibleError` | `BusinessError` | 422 | subscription_status no elegible para retry |

Nota: `BusinessError` → HTTP 422 (no 400). `SavedCardRejectedError` usa 402 para que el
frontend pueda distinguir rechazo de tarjeta de un error de servidor. Ver `BACKEND.md`.

Errores de `PATCH /tenants/{id}/plan` (dominio `tenants`, no `subscriptions` —
`lambdas/tenants/domain/errors.py`): `TenantPlanChangeNotAllowedError` (422) y
`TenantPlanNotSelfServiceError` (422). Mismo `BusinessError` base, mismo 422.

## Campos De Suscripcion En Tenant

```python
dlocal_payer_id                        str | None  — payer_id de la ultima confirmacion SmartFields;
                                                     habilitado cobra automatico y retry-payment
subscription_status                    str | None  — "active" | "expired" | "pending_payment"
                                                     | "payment_failed" | None
plan_cycle_ends_at                     str | None  — ISO8601 UTC; None cuando pending_payment
subscription_renewal_reminder_sent_at  str | None  — idempotencia del worker diario
pending_order_id                       str | None  — order_id PAID pendiente de activar;
                                                     se escribe en Phase 1 de activate,
                                                     se limpia al activar exitosamente.
                                                     Sirve de señal para el guard y el reconciliador.
plan_confirmed_at                      str | None  — seteado por ChangePlanUseCase (ver
                                                     "Confirmar/Cambiar Plan Post-Registro");
                                                     null para siempre en tenants creados
                                                     antes de 2026-06-21 (no afecta porque
                                                     esos ya tienen cert_uploaded_at).
```

Metodos de dominio relevantes:

```python
tenant.mark_payment_failed(*, updated_by)          # subscription_status = "payment_failed"
tenant.apply_subscription_renewal(...)             # subscription_status = "active"; limpia reminder
tenant.expire_subscription(*, updated_by)          # subscription_status = "expired"
```

`subscription_status` es gestionado por nuestra logica (no por dLocal).

`activate_subscription(payer_id, plan_cycle, now, updated_by)` — primera activacion:
setea `plan_cycle_ends_at = now + ciclo`, `subscription_status="active"`, `dlocal_payer_id`,
y limpia `pending_order_id = None`. Opuesto a `apply_subscription_renewal` que usa
`max(now, plan_cycle_ends_at)` para no perder dias del ciclo anterior.

`apply_subscription_renewal(payer_id, plan_cycle, now, updated_by)` — renovacion: extiende
`plan_cycle_ends_at` desde `max(now, plan_cycle_ends_at)`, setea `subscription_status="active"`,
actualiza `dlocal_payer_id` con el payer_id del cobro, limpia `subscription_renewal_reminder_sent_at`
y, si el tenant estaba `SUSPENDED`, lo devuelve a `ACTIVE` (permite reactivar expirados que pagaron).

`expire_subscription(updated_by)` setea `subscription_status="expired"` **y** `status=SUSPENDED`
(el tenant pierde acceso al dashboard hasta que renueve).

`confirm_plan_selection(plan_id, plan_limit_cycle, plan_is_free, updated_by)` — usado por
`ChangePlanUseCase`: cambia `plan_id`, limpia `pending_order_id`, y rehace el mismo
branching libre/pago que `Tenant.create()` (gratis → `subscription_status=None` +
`plan_cycle_ends_at = now + ciclo`; pago → `subscription_status='pending_payment'` +
`plan_cycle_ends_at=None`), y setea `plan_confirmed_at = now()`.

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
- `schemas.ts` — `createPaymentResultSchema` (incluye `net_amount`, `markup_pct`),
  `confirmPaymentResultSchema`, `paymentStatusSchema`, `applyRenewalResultSchema`,
  `retryPaymentResultSchema`
- `api.ts` — `subscriptionsApi.{createPayment, confirmPayment, getPayment,
  activateSubscription, applyRenewal, retryPayment}`
- `components/PendingActivationBanner.tsx` — banner sticky que auto-activa con retry
  y muestra "Reintentar" si falla. Se monta desde `(tenant)/_layout.tsx` cuando
  `pending_payment + pending_order_id`.
- `components/PaymentFailedBanner.tsx` — auto-reintenta `retry-payment` al montar.
  En exito llama `onRetried()`. En fallo muestra dos botones: "Reintentar tarjeta
  guardada" (llama retry-payment de nuevo) y "Pagar con tarjeta nueva" (navega a billing).
  Se monta desde `(tenant)/_layout.tsx` cuando `subscription_status === 'payment_failed'`.
- `components/PriceBreakdown.tsx` — muestra desglose: plan, precio base, comision 12%,
  total a cobrar. Props: `plan`, `netAmount?`, `grossAmount?`. Si no tiene `netAmount`/
  `grossAmount`, calcula el gross en el cliente con `MARKUP_PCT = 0.12`.
- `dlocal-types.ts` — interfaces TypeScript del SDK dLocal Go.
- `dlocal-field-options.ts` — estilos del campo SmartFields adaptados al tema activo.
- `use-dlocal-smartfields.ts` — hook React que encapsula carga del SDK, inicializacion,
  mount/unmount y estados `sdkReady`/`sdkError`. StrictMode-safe con flag `cancelled`.

`frontend/features/tenants/hooks/usePlan.ts` — `usePlan(planId)`: carga `plansApi.list()`
y filtra por `planId`. Devuelve `{ plan, loading }`. Usado en `ActivateSubscriptionScreen`,
`BillingScreen` y `PaymentFailedBanner` para mostrar nombre y precio del plan.

`frontend/lib/utils/retry.ts` — `retryWithBackoff(fn, [1000, 2000, 4000])`. Utilitario
generico; usado en `ActivateSubscriptionScreen`, `BillingScreen` y `PendingActivationBanner`.

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

- **Confirmar/Cambiar Plan** (primera sesion, antes de pagar): ver "Confirmar/Cambiar
  Plan Post-Registro" arriba — `ConfirmPlanScreen`, ruta `/(app)/confirm-plan`.

- **Activacion** (primera sesion): `frontend/features/subscriptions/screens/ActivateSubscriptionScreen.tsx`
  Ruta: `/(app)/activate-subscription` — fuera de `(tenant)/` para evitar loop del guard.
  Guard: `(tenant)/_layout.tsx` detecta `pending_payment` sin `pending_order_id` y redirige aqui.
  Flujo: `useTenant` + `usePlan` cargan → `createPayment` se llama **automaticamente** al montar
         (guard `useRef(false)` para evitar doble disparo en StrictMode) → `PriceBreakdown`
         muestra el desglose mientras el SDK carga → formulario pagador → `confirmPayment`
         → `activateSubscription` (con retry) → redirect dashboard.
  Si el usuario cancela, el `useRef` se resetea para poder reintentar.

- **Billing** (renovacion / pago con tarjeta nueva desde payment_failed):
  `frontend/features/tenants/screens/BillingScreen.tsx`
  Adapta su UI cuando `subscription_status === 'payment_failed'` (titulo, hint, badge).
  Flujo: `createPayment` → SDK SmartFields → `PriceBreakdown` → formulario pagador
         → `confirmPayment` → `applyRenewal` (con retry).
  `ApplySubscriptionRenewalUseCase` no valida el subscription_status — acepta `payment_failed`
  y deja el tenant en `active` si el pago es PAID.
  **Sin pago anticipado:** cuando `subscription_status ===
  'active'`, `BillingScreen` no muestra el card de pago — muestra un card informativo
  ("Tu suscripción está al día") en su lugar. El card de pago manual ("Renovar
  suscripción"/"Pagar con tarjeta nueva") solo aparece para `expired`/`payment_failed`
  (o el estado neutro sin suscripcion todavia, que en la practica no deberia alcanzar
  esta pantalla porque `pending_payment` se intercepta antes en `(tenant)/_layout.tsx`).
  No existe una regla de "ultimos N dias antes de vencer" — si se necesita, es una
  decision de negocio nueva a definir aqui, no solo un ajuste de UI.

- **Guard con banners** `(tenant)/_layout.tsx` (orden exacto, cada uno solo se evalua si
  el anterior no aplico):
  1. `!plan_confirmed_at && !cert_uploaded_at` → redirect a `ConfirmPlanScreen`
  2. `pending_payment` + `pending_order_id` → muestra Stack + `PendingActivationBanner`
  3. `pending_payment` sin `pending_order_id` → redirect a `ActivateSubscriptionScreen`
  4. `payment_failed` → muestra Stack + `PaymentFailedBanner` encima (acceso al dashboard permitido)
  5. `!cert_uploaded_at` → redirect a `UploadCertificateScreen` (ver `CERTIFICATES.md`)
  6. cualquier otro estado → pass-through (dashboard)

## Workers De Suscripcion

| Worker | Schedule | Funcion |
| --- | --- | --- |
| `subscription_renewal_notifier` | `cron(0 10 * * ? *)` (diario) | Recordatorio 7d antes; vencimiento; cobro automatico si tiene payer_id |
| `pending_activation_reconciler` | `rate(5 minutes)` | Activa tenants con `pending_payment + pending_order_id` |

El `subscription_renewal_notifier` requiere `PLANS_TABLE`, `PAYMENTS_TABLE` y
`DLOCALGO_CREDENTIALS_NAME` para habilitar el cobro automatico. Si alguna variable
falta, el worker funciona en modo degradado (solo notificaciones, sin auto-charge).

El scan `list_with_subscription_expiry_due` incluye tenants con `subscription_status`
`active` **y** `payment_failed`, para que la logica de gracia y reintento funcione
en corridas subsecuentes del worker. Tenants en otros estados no son recogidos.

Grace period: 7 dias desde `plan_cycle_ends_at`; tras agotarse expira sin reintentar.
Email de pago fallido: una sola vez por ciclo (no se reenvía en reintentos).

## Deuda Tecnica

- Scans en workers (`list_with_subscription_expiry_due`, `list_with_pending_activation`)
  usan scan completo — aceptables hasta ~10 K tenants activos; migrar a GSI cuando la
  cardinalidad lo requiera.
- Webhook dLocal no tiene DLQ ni alerta: si el handler falla repetidamente, no hay
  mecanismo para detectar perdida de eventos mas alla de los logs de Lambda.
- Orders con status `PENDING` (3DS iniciado pero no completado) no tienen limpieza
  automatica — quedan indefinidamente en DynamoDB sin un worker que los expire o notifique.
- `PATCH /tenants/{id}/plan` no tiene rate limit ni tope de cambios — un tenant podria
  alternar entre planes repetidamente antes de pagar. Cada cambio a un plan gratis
  resetea `plan_cycle_ends_at` a `now + ciclo`, lo cual es inocuo en este punto del flujo
  (el tenant todavia no emitio nada), pero no hay un test que documente ese
  comportamiento como deliberado vs. casual.
- Si un `Payment` quedo `CREATED`/`PENDING` con `tenant_id` vacio (creado desde
  `ActivateSubscriptionScreen` antes de cambiar de plan) y el tenant cambia de plan via
  `PATCH /tenants/{id}/plan`, ese payment queda huerfano (mismo patron que pagos
  abandonados sin confirmar) — no hay limpieza automatica, mismo punto que el de arriba
  sobre orders `PENDING`.
