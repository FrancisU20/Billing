# Onboarding & Certificados — Dominio

Estado: **implementado base**. El flujo productivo usa OTP por correo y certificado
digital p12 valido antes de crear tenants self-service.

## Lee Tambien Antes De Empezar

Leer estos archivos en orden antes de escribir codigo en este dominio:

| Archivo | Por que |
| --- | --- |
| `CLAUDE.md` | Reglas no negociables (seguridad, git) |
| `BACKEND.md` | Outbox transaccional, idempotencia, patron Secrets Manager |
| `FRONTEND.md` | Wizard multi-paso, design system, patrones de pantalla |
| `TENANTS.md` | Campos nuevos en `Tenant`, RUC lock, `sri_environment` |
| `PLANS.md` | Campos `pruebas_*`, `dedicated_queue`, seleccion de plan en el registro |
| `AUTH.md` | `AdminCreateUser`, challenge `NEW_PASSWORD_REQUIRED` tras el registro |
| `CERTIFICATES.md` | Validacion p12, RUC del certificado, almacenamiento y reemplazo posterior |

## Proposito

Registro publico self-service del tenant. Un cliente llega al sitio, elige su plan,
ingresa datos de empresa, sube su certificado digital p12, verifica su email con OTP
y queda operativo sin intervencion del superadmin.

La cuenta arranca en `sri_environment=testing` con los limites del plan elegido. El
tenant puede activar produccion desde su dashboard cuando este listo.

El dominio tambien cubre la gestion del ciclo de vida del certificado (actualizacion,
alertas de vencimiento).

## Componentes

Lambdas involucrados:

- `backend/lambdas/onboarding/` — registro publico con OTP (sin JWT)
- `backend/lambdas/certificates/` — gestion posterior del certificado (PUT/GET, con JWT)
- `backend/lambdas/workers/tenant_onboarding` — worker async ya existente; crea usuario Cognito
- `backend/lambdas/workers/email_notifications` — envia OTP, bienvenida y leads Enterprise

Servicios AWS:

- **DynamoDB tabla `tenants`** — campos nuevos que hay que agregar al modelo (ver abajo)
- **AWS Secrets Manager** — almacena el p12 cifrado; NUNCA DynamoDB ni S3 plano
- **Amazon Cognito** — `AdminCreateUser` para generar clave temporal

Frontend:

- `frontend/features/onboarding/`
- `frontend/app/(public)/register/` (sin auth)

## Campos De Onboarding En Tenant

Campos actuales en `backend/lambdas/tenants/domain/tenant.py` y la tabla DynamoDB
`tenants`:

```python
sri_environment: Literal["testing", "production"]  = "testing"
certificate_secret_arn: str | None                  = None
cert_subject_ruc: str | None                        = None
cert_expires_at: str | None                         = None
cert_issuer: str | None                             = None
cert_uploaded_at: str | None                        = None
cert_expiry_alert_60_sent_at: str | None            = None
cert_expiry_alert_30_sent_at: str | None            = None
onboarding_completed_at: str | None                 = None
```

`cert_expiry_alert_60_sent_at` / `cert_expiry_alert_30_sent_at`: usados por el worker
`certificate_expiry_notifier` para no repetir alertas de caducidad; se resetean a
`None` cuando se sube un certificado nuevo (ver `CERTIFICATES.md`).

`address` (dirMatriz) y `accounting_required` (obligadoContabilidad en infoTributaria) ya
existen en `Tenant` (ver `TENANTS.md`) y se capturan en el wizard (paso 2, junto a
RUC/razon social) porque son obligatorios en `<infoTributaria>` del XML SRI desde el
primer documento (incluso en `pruebas`). Pedirlos despues del onboarding implicaria una
campana de completado de datos sobre tenants ya activos.

## Campos Nuevos En Plan

Ya existen en `Plan` (ver `PLANS.md`):

```python
pruebas_monthly_docs_limit: int  # docs individuales/mes en pruebas; -1 = ilimitado
pruebas_monthly_bulk_limit: int  # docs bulk/mes en pruebas; -1 = ilimitado
dedicated_queue: bool            # True en plan Enterprise — SQS FIFO propia
self_service: bool               # False en plan Enterprise — ver "Flujo Enterprise"
```

Valores por plan (ver tabla completa en `PLANS.md`):

| Plan (slug) | docs/mes prod | docs/mes pruebas | bulk pruebas | dedicated_queue | self_service |
| --- | --- | --- | --- | --- | --- |
| free | 20 | 20 | 0 | false | true |
| basic | 50 | 50 | 0 | false | true |
| pyme | 300 | 200 | 50 | false | true |
| pro | 1000 | 500 | 200 | false | true |
| enterprise | -1 | -1 | -1 | true | false |

`self_service=false` no significa que el plan esta oculto del catalogo publico (`GET /plans`
sigue devolviendolo, para que el cliente pueda elegirlo en el wizard) — significa que
`POST /onboarding/otp/confirm` con ese `plan_id` toma la rama "lead capture" en vez de
crear el tenant.

## Entornos SRI

| Valor | Significado |
| --- | --- |
| `"testing"` | Documentos de prueba, sin validez legal. URL SRI de certificacion. |
| `"production"` | Documentos reales con validez tributaria. URL SRI de produccion. |

Reglas:

- Todo tenant nuevo nace en `"testing"`.
- El switch a produccion es self-service desde el dashboard del tenant.
- El campo `sri_environment` del tenant dicta el valor del campo `ambiente` en el XML del SRI.
  No hay forma de "enviar a produccion desde pruebas" por accidente: lo dicta el tenant, no el caller.
- El certificado digital es el mismo para ambos entornos. Lo que cambia es la URL del WebService SRI.

## Flujo De Registro — Paso A Paso

Aplica solo a planes con `self_service=true`. Para `self_service=false` (Enterprise), ver
"Flujo Enterprise — Lead Capture" mas abajo.

```
1. GET /plans (publico) — cliente ve planes disponibles
2. Formulario (frontend):
   - RUC (13 digitos), razon social, nombre comercial, email, telefono opcional
   - Archivo p12 + clave del certificado
3. POST /onboarding/otp/request (publico, sin JWT)
   Body: { ruc, trade_name, legal_name, email, phone?, plan_id,
           certificate_b64, cert_password }

4. Handler valida y ejecuta en orden:
   a. Verifica que plan_id existe, esta activo y self_service=true
      (si self_service=false, ver "Flujo Enterprise — Lead Capture"; no pide p12)
   b. `shared.certificates.CertificateValidator.validate_base64(...)`:
      - Parsear p12 (falla si archivo corrupto o password incorrecta)
      - Extraer RUC del Subject del certificado
      - Comparar RUC del cert contra RUC del body → si difiere: CertificateRucMismatchError
      - Verificar expiry → si vencido: CertificateExpiredError
      - No se valida el emisor (CA) — ver "Errores" en CERTIFICATES.md
   c. Verifica que el RUC no esta en uso
      - Validar el certificado primero (paso b) evita exponer disponibilidad de RUC a quien
        no tiene un certificado valido para ese RUC (enumeracion).
   d. Crea registro temporal `ONBOARDING_VERIFICATION`:
      - OTP hasheado, nunca plano
      - TTL 10 minutos
      - intentos maximos 5
      - no guarda p12 ni cert_password
   e. Envia OTP al email

5. [Solo planes de pago] Frontend navega a payment.tsx:
   - RegisterOtpScreen detecta `isPaidPlan` → guarda `otpValue` en store → navega a
     `Routes.public.registerPayment` (SIN llamar a /otp/confirm todavia)
   - RegisterPaymentScreen crea orden PayPal on mount
   - Usuario aprueba en navegador del sistema (Linking.openURL con paypalApprovalUrl)
   - "Ya completé el pago" → getPayment → capturePayment si APPROVED → guarda order_id en store
   - Llama /otp/confirm con order_id incluido

   [Planes gratuitos] Frontend llama /otp/confirm directamente sin order_id.

6. POST /onboarding/otp/confirm (publico, sin JWT)
   Body: { verification_id, otp, ruc, trade_name, legal_name, email, phone?, plan_id,
           certificate_b64, cert_password, order_id? }

   (El campo `order_id` esta en `_IGNORED_FIELDS` de `payload_signature.py` — no afecta
   el hash de integridad; el hash se calcula sin el, tanto en request como en confirm.)

7. Handler confirma:
   a. Verifica OTP, expiracion e intentos
   b. Revalida certificado p12 completo contra el RUC
   c. Si plan es de pago (`not plan.is_free`): verifica via `IPaymentVerifier`:
      - `order_id` debe estar presente en body → `OnboardingPaymentRequiredError` (422) si no
      - Payment debe existir → 422 si no encontrado
      - Payment.status debe ser CAPTURED → 422 si no
      El `IPaymentVerifier` lee la tabla `payments` sin acoplar el dominio onboarding a infra.
   d. Secrets Manager PutSecretValue:
      - Path: /codelabs-billing/{env}/tenant/{tenant_id}/certificate
      - Contenido: { "p12_b64": "...", "password": "..." }
      - Si DynamoDB falla luego, el handler intenta limpiar el secreto huerfano.
   e. DynamoDB TransactWriteItems:
      - Tenant (status=active, sri_environment=testing, certificate metadata)
      - RUC lock — MISMO mecanismo `RUC#{ruc}` / `TENANT_RUC_LOCK` de TENANTS.md.
      - Idempotency record
   f. Outbox: encola evento TenantCreatedEvent
      - El worker tenant_onboarding llama AdminCreateUser con clave temporal
      - Worker email_notifications envia email con clave temporal

8. Respuesta: { success: true, data: { tenant_id, email } }
9. Cliente recibe email con clave temporal
10. Cliente hace login → challenge NEW_PASSWORD_REQUIRED → cambia clave
11. Dashboard arranca en sri_environment=testing
```

## Flujo Enterprise — Lead Capture (`self_service=false`)

El plan Enterprise no se aprovisiona automaticamente. El cliente llena el mismo wizard
publico, pero el resultado es un contacto comercial, no un tenant operativo.

```
1. GET /plans (publico) — Enterprise aparece en el catalogo igual que los demas
2. Formulario (frontend):
   - RUC, razon social, nombre comercial, email, telefono opcional
   - Paso de certificado (paso 3 del wizard) se OMITE para este plan
3. POST /onboarding/otp/request (publico, sin JWT)
   Body: { ruc, trade_name, legal_name, email, phone?, plan_id }
   (sin certificate_b64 / cert_password)

4. Handler:
   a. Verifica que plan_id existe, esta activo y self_service=false
   b. Envia OTP al email y crea `ONBOARDING_VERIFICATION` sin p12
5. POST /onboarding/otp/confirm
   a. Verifica OTP
   b. NO toma RUC lock, NO crea Tenant, NO llama Cognito, NO usa Secrets Manager
   c. Crea registro `ENTERPRISE_LEAD` (tabla `tenants`, PK nueva, entity_type distinto —
      no colisiona con el lock `RUC#{ruc}` de tenants reales)
   d. Outbox: encola evento ENTERPRISE_LEAD_CREATED
      - Worker email_notifications envia email a ti (superadmin) con los datos del lead

6. Respuesta: { success: true, data: { message: "nos pondremos en contacto contigo" } }
   El frontend muestra pantalla de confirmacion distinta a la del flujo self-service
   (sin instrucciones de login, sin clave temporal).
```

Conversion manual: cuando contactas al cliente y se cierra el plan, el superadmin crea el
tenant real via `POST /tenants` (flujo admin existente) usando los datos del
lead, y provisiona la queue dedicada manualmente (ver "Plan Enterprise Y Queue Dedicada").
El registro `ENTERPRISE_LEAD` no se convierte automaticamente — queda como historico.

## Manejo De Errores En La Creacion

La creacion involucra 3 sistemas no-transaccionales entre si (Secrets Manager, DynamoDB,
Cognito). El orden minimiza tenants incompletos:

| Paso | Si falla | Estado resultante |
| --- | --- | --- |
| Validacion p12 | error de negocio | nada quedo creado |
| Secrets Manager | error externo | no se crea tenant |
| DynamoDB transaction | rollback automatico; se intenta limpiar secreto | no se crea tenant |
| Cognito via outbox | outbox reintenta | tenant creado; usuario se recupera async |

Si un tenant existente necesita cambiar el certificado, usa `PUT /tenants/{id}/certificate`
en la Lambda `certificates`.

## Validador De Certificado

Archivo: `backend/shared/certificates/validator.py`
Dependencia: `cryptography` (agregar a `backend/requirements.txt`).

```python
from cryptography.hazmat.primitives.serialization import pkcs12
from datetime import datetime, timezone

def validate_and_extract(p12_bytes: bytes, password: str) -> CertificateMetadata:
    # 1. Parsear — ValueError si password incorrecta o archivo corrupto
    private_key, cert, _ = pkcs12.load_key_and_certificates(
        p12_bytes, password.encode()
    )
    # 2. Extraer RUC (o cedula de persona natural) del Subject
    subject_identifier = _extract_identifier_from_subject(cert.subject)
    # 3. Verificar expiry
    if cert.not_valid_after_utc < datetime.now(timezone.utc):
        raise CertificateExpiredError(...)
    # No se valida el emisor (CA): el SRI es quien decide si acepta la firma.
    issuer = _extract_issuer_name(cert.issuer)
    return CertificateMetadata(subject_identifier, cert.not_valid_after_utc, issuer)
```

### Extraccion Del RUC Segun CA

El campo que contiene el RUC varia por emisor del certificado. Hay que manejar al menos:

| CA | Campo en Subject |
| --- | --- |
| Banco Central del Ecuador | `SERIALNUMBER` o `CN` con prefijo `RUC:` |
| Security Data | `SERIALNUMBER` |
| ANF | `SERIALNUMBER` |

La funcion `_extract_ruc_from_subject` debe probar los campos en orden y normalizar el
resultado a los 13 digitos del RUC. Si no se extrae RUC, lanzar `CertificateRucNotExtractableError`
para que el mensaje al usuario sea claro (no un generico "invalido").

## Lambda `certificates` — Gestion Post-Onboarding

Permite al tenant actualizar su certificado sin pasar por onboarding de nuevo.

```
PUT /tenants/{id}/certificate    — owner/admin del tenant o superadmin
  Body: { certificate_b64, cert_password }
  Misma validacion que en onboarding.
  Actualiza DynamoDB + Secrets Manager.

GET /tenants/{id}/certificate    — owner/admin del tenant o superadmin
  Devuelve solo metadatos: cert_subject_ruc, cert_expires_at, cert_issuer, cert_uploaded_at.
  NUNCA devuelve el p12 ni la password.
```

Nombres en Secrets Manager (nombre determinístico — un solo secreto por tenant, se
sobreescribe en cada actualizacion):

```
/codelabs-billing/{env}/tenant/{tenant_id}/certificate
Contenido: { "p12_b64": "...", "password": "..." }
```

`PUT` sobreescribe el mismo secreto (`put_secret_value`). Secrets Manager retiene
automaticamente la version inmediatamente anterior (`AWSPREVIOUS`), pero eso no es un
historico de certificados — se pierde en la siguiente actualizacion. Si en el futuro se
necesita historico de certificados con validez legal (auditoria de que certificado firmo
que documento), debe disenarse explicitamente (ej. secretos versionados por timestamp o
tabla de historico); no asumir que Secrets Manager lo provee.

### Consistencia Tenant ↔ Secrets Manager En `PUT`

El flujo es: validar p12 → escribir secreto (Secrets Manager) → `commit()` transaccional
en DynamoDB con optimistic lock (`version`). Si `commit()` falla por
`OptimisticLockError` (modificacion concurrente del mismo tenant), el handler reintenta
hasta 3 veces: re-obtiene el tenant en su version actual y reaplica la metadata del
certificado ya validado (sin re-validar el p12 ni re-escribir el secreto, porque
`put_certificate` es idempotente sobre el mismo nombre de secreto). Si los 3 intentos
fallan, se devuelve `OPTIMISTIC_LOCK_ERROR` (409) al cliente.

## Secrets Manager — Costos

- $0.40 USD/secreto/mes.
- 1000 tenants = $400/mes.
- Si el costo es inaceptable en escala, evaluar Parameter Store SecureString ($0.05/10k calls,
  sin cargo por secreto). Diferencia: sin rotacion automatica ni auditoria avanzada de SM.
- Decision a tomar cuando el volumen de tenants lo justifique.

## Estructura De Carpetas — Lambda onboarding

Estructura actual (Fases 1 y 2 ya consolidadas; el registro siempre pasa por OTP):

```
backend/lambdas/onboarding/
  handler.py
  schemas.py           # OnboardingRequest DTOs (Pydantic)
  domain/
    commands.py        # RequestOnboardingOtpCommand, ConfirmOnboardingOtpCommand
    errors.py          # reexporta PlanNotFoundError/PlanNotActiveError de plans + errores OTP
    events.py          # EnterpriseLeadCreatedEvent, OnboardingOtpRequestedEvent
    enterprise_lead.py # EnterpriseLead dataclass + create()
    onboarding_verification.py
    repositories/
      i_plan_catalog.py                  # ABC + PlanSummary
      i_enterprise_lead_repository.py
      i_onboarding_verification_repository.py
  use_cases/
    request_onboarding_otp.py    # valida certificado + RUC, crea ONBOARDING_VERIFICATION, envia OTP
    confirm_onboarding_otp.py    # verifica OTP, rama self-service (Tenant) vs lead (EnterpriseLead)
    payload_signature.py         # hash de integridad request<->confirm
  infra/
    plan_catalog.py                   # adapta PlanRepository a IPlanCatalog
    enterprise_lead_repository.py     # DynamoDB tabla `tenants`, entity_type=ENTERPRISE_LEAD
    onboarding_verification_repository.py
    onboarding_commit_repository.py   # transaccion OTP + Tenant/EnterpriseLead

backend/shared/certificates/
  validator.py
  store.py
  metadata.py
  errors.py
```

Reusa sin reimplementar: `lambdas.tenants.domain.tenant.Tenant`/`Tenant.create()`,
`lambdas.tenants.domain.events.TenantCreatedEvent`,
`lambdas.tenants.infra.tenant_repository.DynamoTenantRepository.commit()` (RUC lock +
audit + idempotency + outbox), `lambdas.plans.infra.plan_repository.DynamoPlanRepository`.

## Rutas CDK

```python
# infra/stacks/api_stack.py

# Publicas (sin JWT authorizer):
(HttpMethod.POST, "/onboarding/otp/request")
(HttpMethod.POST, "/onboarding/otp/confirm")

# Autenticadas:
(HttpMethod.PUT,  "/tenants/{id}/certificate")
(HttpMethod.GET,  "/tenants/{id}/certificate")
```

Las rutas publicas de onboarding usan throttling nativo de API Gateway HTTP API por ruta.
No usar WAF para este proyecto mientras el control de costo sea prioridad.

## Frontend — Wizard De Registro

La seleccion de plan (paso 1) ya no es una ruta separada: vive embebida en la landing
page publica (`/`, `features/marketing/components/PlansSection.tsx`), que reusa
`usePlans()` y al elegir un plan llama `selectPlan()` y navega a `details`.

Rutas en `frontend/app/(public)/register/`:

```
details.tsx      # paso 2: datos empresa (RUC, razon social, contacto, contabilidad) -> RegisterDetailsScreen
certificate.tsx  # paso 3: p12 + clave; se omite si plan.self_service=false
otp.tsx          # paso 4: confirmacion OTP
payment.tsx      # paso 5 (solo planes de pago): pago PayPal -> RegisterPaymentScreen
confirm.tsx      # confirmacion — mensaje distinto segun self_service (login vs "te contactaremos") -> RegisterConfirmScreen
```

Si el store no tiene `selectedPlan`/`result` (usuario entra directo a `details` o
`confirm`), ambas pantallas redirigen a `Routes.root` (`/`), donde puede elegir un plan.
`RegisterPaymentScreen` tambien verifica `otpValue` en store — si no esta, redirige a root.

Feature: `frontend/features/onboarding/` — `schemas.ts`, `api.ts`, `form.ts`, `store.ts`
(Zustand: `selectedPlan`, `formValues`, `certificateValues`,
`otpRequestIdempotencyKey`, `otpConfirmIdempotencyKey`, `verification`, `result`,
`otpValue`, `orderId`),
`components/RegistrationForm.tsx`,
`screens/Register{Details,Certificate,Otp,Payment,Confirm}Screen.tsx`.

Logica de bifurcacion en `RegisterOtpScreen`:
- `isPaidPlan(monthly_price, annual_price)` — `parseFloat(price) > 0`
- Si es de pago: `setOtpValue(otp)` + `router.push(registerPayment)` (sin llamar confirm)
- Si es gratis: llama `confirmOtp` directamente como antes

- `hooks/useRequestOtp.ts`: encapsula la llamada a `/onboarding/otp/request` +
  `setVerification`, con navegacion a `otp` por defecto (`options?.navigate`, default
  `true`). Usado por `RegisterDetailsScreen` (planes no self-service, sin certificado)
  y `RegisterCertificateScreen` (planes self-service, con certificado) sin pasar
  `options`. Si se agrega un paso intermedio que tambien dispare OTP, reusar este hook
  en vez de duplicar la llamada.
- `RegisterOtpScreen`: si el codigo no llega o expira, el boton "Reenviar codigo" llama
  a `useRequestOtp` con `{ navigate: false }` (mismo payload que `confirmOtp`, sin
  `otp`/`verification_id`) y muestra confirmacion inline; "Volver" hace `router.back()`
  al paso anterior (`certificate` o `details` segun `selectedPlan.self_service`) sin
  perder el estado del wizard (store en memoria persiste mientras el stack no se
  desmonta).
- `otpConfirmIdempotencyKey` se genera una sola vez en `selectPlan()` (lazy, `??`) y
  no se rota — a diferencia de `otpRequestIdempotencyKey`, que `setVerification`
  rota tras cada `/otp/request` exitoso.

- El p12 viaja en el body como base64 (archivos tipicos < 10 KB, limite backend 50 KB).
- El selector inicial de p12 en frontend es web nativo (`input[type=file]`). Si se habilita
  onboarding movil nativo, reemplazar por `expo-document-picker` manteniendo el mismo
  contrato `{ certificate_b64, cert_password }`.
- Nunca loguear ni mostrar la password del certificado.
- Validar RUC localmente antes de enviar. No reemplaza validacion backend.
  Implementado en `frontend/lib/utils/ruc.ts` (`isValidRuc`/`isValidCedula`), portado
  desde `backend/shared/domain/value_objects/ecuador_identification.py`.
  **El algoritmo depende del 3er digito del RUC** — no es un solo modulo:
  - 3er digito 0-5 (persona natural / RIMPE): cedula (modulo 10) + sufijo `001`.
  - 3er digito 9 (sociedad privada): modulo 11 con coeficientes de sociedades.
  - 3er digito 6 (entidad publica): modulo 11 con coeficientes de entidad publica.
  Implementar los 3 casos tanto en frontend (validacion temprana) como backend
  (`certificate_validator` o un `ruc_validator` compartido en `_base`). Un solo
  algoritmo generico rechaza RUCs validos de sociedades o acepta RUCs invalidos
  de persona natural.
- **Idempotency-Key**: generar dos UUIDs al seleccionar el plan:
  `otpRequestIdempotencyKey` para `POST /onboarding/otp/request` y
  `otpConfirmIdempotencyKey` para `POST /onboarding/otp/confirm`. No reutilizar la misma
  key en ambas rutas porque el backend la ata a method+path+body.
  Tras recibir una verificacion OTP exitosa, rotar `otpRequestIdempotencyKey` para que
  volver al paso anterior y pedir un codigo nuevo no devuelva la respuesta cacheada.

## Errores De Dominio

- `CertificateInvalidError` — p12 corrupto o password incorrecta
- `CertificateExpiredError` — el certificado ya vencio
- `CertificateRucMismatchError` — el RUC del cert no coincide con el RUC del tenant
- `CertificateRucNotExtractableError` — no se pudo extraer el RUC del Subject del cert

## Edge Cases Y Trampas

- **"Certificado valido pero el sistema dice que no"**: caso mas probable = extraccion de RUC
  falla para esa CA especifica. El campo varia (SERIALNUMBER, CN, OID propio). Primero loguear
  el Subject completo del certificado (sin la clave privada) para ver que campos trae.

- **Tamano del p12**: certificados reales son 3-8 KB. Si alguien sube un PDF renombrado `.p12`,
  el parseo falla limpiamente con `CertificateInvalidError`. Agregar limite de 50 KB en el handler
  antes de llamar al validador.

- **Clave del certificado perdida**: si el tenant pierde la clave del p12, los bytes almacenados
  en Secrets Manager son inutilizables. Deben subir el certificado de nuevo con la clave correcta.
  Documentar esto claramente en el onboarding.

- **Cognito `AdminCreateUser` falla despues de DynamoDB commit**: el tenant existe pero sin
  usuario Cognito. El outbox reintenta. Si el reintento falla definitivamente, el superadmin
  puede re-encolar el evento o crear el usuario manualmente.

- **Email con typo en el registro**: el RUC lock es permanente (paso d) pero el usuario
  Cognito se crea async con el email del formulario (paso f). Si el email tiene un error
  de tipeo, la empresa queda con el RUC bloqueado y sin acceso, sin que nadie lo note hasta
  que el cliente reclama. Recuperacion: corregir `email` con
  `PATCH /tenants/{id}` y luego llamar
  `POST /tenants/{id}/onboarding/retry`, que re-encola `TenantCreatedEvent`
  para reintentar `AdminCreateUser`/reset de clave temporal y email de bienvenida.

- **Un email = un tenant**: Cognito exige username (email) unico por User Pool, y el
  onboarding no implementa logica especial para permitir el mismo email en varios tenants
  (ej. un contador con varios RUCs). Si el email ya esta registrado, el registro se
  rechaza con un error claro (`EmailAlreadyRegisteredError` o equivalente). Esto es
  intencional, no un bug: el caso "un usuario administra varios tenants" se resuelve a
  futuro con un modelo de membresias (ver `AUTH.md` → "Memberships / Multi-tenant
  Switch"), no relajando la unicidad de email en onboarding.

## Plan Enterprise Y Queue Dedicada

Plan Enterprise (`dedicated_queue=True`, `self_service=False`) no pasa por onboarding
automatico (ver "Flujo Enterprise — Lead Capture"). La queue dedicada se provisiona
manualmente cuando el superadmin convierte el lead en tenant real:

- Opcion v1: `boto3 sqs.create_queue(FifoQueue=True)` ejecutado manualmente o via script
  del superadmin. Rapido pero la queue no esta en CDK stack.
- Opcion v2 (mas limpio): agregar el `tenant_id` a SSM Parameter Store, CDK pipeline
  provee la queue en el siguiente deploy.
- El ARN de la queue se guarda en `tenant.dedicated_queue_url`.

No hay trabajo de provisioning automatico en el worker `tenant_onboarding` para este caso —
ese worker solo corre para tenants `self_service=true`.

## Checklist De Implementacion

### Backend — Fase 1 (completado)

- [x] Campos nuevos en `Plan`: `pruebas_monthly_docs_limit`, `pruebas_monthly_bulk_limit`, `dedicated_queue`, `self_service`
- [x] Campos nuevos en `Tenant`: `legal_name`, `accounting_required` (`address` ya existia)
- [x] `ruc_validator` compartido — `is_valid_ruc` ya existia en `ecuador_identification.py`; portado a frontend (`lib/utils/ruc.ts`)
- [x] Migracion: planes existentes con valores default para campos nuevos (Enterprise → `self_service=false`) — `v0003_backfill_onboarding_fields`
- [x] Lambda `onboarding`: estructura completa, rama self-service (Tenant) y rama lead (Enterprise), tests (`test_handler.py`)
- [x] Entidad `ENTERPRISE_LEAD` en tabla `tenants` + outbox `EnterpriseLeadCreatedEvent`
- [x] Worker `email_notifications`: nueva plantilla para `EnterpriseLeadCreatedEvent` (notificacion a `SUPERADMIN_EMAIL`)
- [x] CDK: `onboarding_api_fn` inicial; Fase 2 reemplazo el endpoint publico inicial por
  `/onboarding/otp/request` y `/onboarding/otp/confirm`

### Backend — Fase 2 (completado base, certificado + OTP)

- [x] `cryptography` en `backend/requirements.txt`
- [x] Campos de certificado en `Tenant`: `certificate_*`, `onboarding_completed_at`
- [x] `shared/certificates` con manejo de RUC por CA
- [x] OTP: `ONBOARDING_VERIFICATION` con TTL, hash e intentos
- [x] Lambda `certificates`: PUT y GET
- [x] CDK: politicas IAM para Secrets Manager y throttling API Gateway por ruta —
  helper `_grant_certificate_secrets` compartido entre `certificates` y `onboarding`;
  `DeleteSecret` solo se otorga a `onboarding` (unico que limpia secretos huerfanos)
- [x] Tests especificos de `CertificateValidator` con p12 generado en memoria: valido,
  clave incorrecta, caducado, RUC distinto, issuer no confiable, RUC no extraible,
  p12 > 50 KB (`test_certificate_validator.py`)
- [x] Tests de la lambda `certificates` (use cases + handler): GET de metadatos,
  control de acceso owner/admin/superadmin, PUT con idempotencia y retry ante
  `OptimisticLockError`
- [x] Tests de dominio `OnboardingVerification` (`test_onboarding_verification.py`):
  creacion, hash de OTP, expiracion, intentos agotados, `mark_used`
- [x] Tests de `RequestOnboardingOtpUseCase`/`ConfirmOnboardingOtpUseCase`
  (`test_use_cases.py`): orden certificado-antes-de-RUC, OTP invalido/expirado/intentos
  agotados, `OnboardingPayloadMismatchError`, RUC ya registrado en confirm, rama
  Enterprise sin certificado
- [x] Worker `certificate_expiry_notifier`: alerta 60 y 30 dias antes de
  `cert_expires_at` (cron diario, ver `CERTIFICATES.md`)

### Frontend — Fase 1 (completado)

- [x] Rutas `/register/*` como publicas (sin layout auth)
- [x] Feature `onboarding/`: schemas Zod, api.ts, form.ts, store.ts (Zustand), `RegistrationForm`
- [x] Wizard de 2 pasos con validacion por paso e Idempotency-Key persistida en el estado del wizard
- [x] Rama Enterprise (`plan.self_service=false`): pantalla de confirmacion "te contactaremos"
- [x] Pantalla de confirmacion con instrucciones de login (planes self-service)

### Frontend — Fase 2 (completado base, certificado + OTP)

- [x] Paso `certificate.tsx` del wizard: file picker web para p12 + clave
- [x] Omitir paso de certificado si `plan.self_service=false`
- [x] Paso `otp.tsx`: ingreso de codigo y mensajes claros

### Backend — Fase 3 (completado — pago obligatorio en onboarding)

- [x] `IPaymentVerifier` en `tenants/domain/repositories/` — abstraccion de verificacion de pago
- [x] `PaymentVerifier` en `tenants/infra/` — lee tabla payments
- [x] `ConfirmOnboardingOtpUseCase`: verifica CAPTURED si plan es de pago
- [x] `OnboardingPaymentRequiredError` (422) si plan de pago sin order_id
- [x] `order_id` en `_IGNORED_FIELDS` de `payload_signature.py`
- [x] Tests actualizados: `FakeOnboardingPlanCatalog` con `is_free=True` como default

### Frontend — Fase 3 (completado — paso payment en wizard)

- [x] `otpValue` y `orderId` en store Zustand
- [x] `RegisterOtpScreen`: bifurcacion planes gratis vs pago (`isPaidPlan`)
- [x] `RegisterPaymentScreen`: crea orden on mount, abre PayPal, captura, llama /otp/confirm
- [x] Ruta `payment.tsx` en `(public)/register/`
- [x] `Routes.public.registerPayment`

## Decisiones Futuras

- Provisioning automatico de queue dedicada Enterprise no esta en scope del flujo actual:
  Enterprise es `lead capture`. Antes de vender Enterprise self-service, decidir entre
  script admin o parametro SSM + CDK.
- Si aparecen nuevas CAs reconocidas por el SRI, actualizar la lista central de emisores
  permitidos en `backend/shared/certificates/validator.py` y cubrir la variante con tests.

## Deuda Solventada

- 2026-06-14: la confirmacion OTP consume `ONBOARDING_VERIFICATION` en la misma transaccion
  que crea el tenant o el `ENTERPRISE_LEAD`; reintentos concurrentes ya no pueden duplicar
  leads ni crear efectos parciales.
- 2026-06-14: el handler de onboarding ya no compone diccionarios DynamoDB; la responsabilidad
  vive en `DynamoOnboardingCommitRepository`.
- 2026-06-14: errores condicionales por OTP ya usado se traducen a `ONBOARDING_OTP_INVALID`
  en vez de `DATABASE_ERROR`.
- 2026-06-14: el frontend rota la idempotency key de request OTP despues de recibir una
  verificacion, permitiendo solicitar un codigo nuevo al volver de paso.
- 2026-06-14: el superadmin puede reintentar onboarding con
  `POST /tenants/{id}/onboarding/retry`; el endpoint escribe audit + outbox +
  idempotencia sin modificar la entidad tenant y valida existencia/version/deleted con
  `ConditionCheck` en la misma transaccion.
