# Certificados Digitales — Dominio

Estado: **implementado**. Validacion p12, almacenamiento en Secrets Manager, endpoint
autenticado PUT/GET, worker de alerta de caducidad y gestion post-onboarding en el
frontend existen. Pendiente: selector nativo movil.

## Lee Tambien Antes De Empezar

| Archivo | Por que |
| --- | --- |
| `CLAUDE.md` | Reglas no negociables de seguridad, costos y git |
| `BACKEND.md` | Clean Architecture, Secrets Manager, idempotencia y permisos |
| `FRONTEND.md` | Patrones de pantalla, formularios y design system |
| `ONBOARDING.md` | Registro inicial usa este dominio para validar el p12 antes de crear tenant |
| `TENANTS.md` | El RUC del certificado debe coincidir con el RUC del tenant |

## Proposito

Validar, almacenar y consultar metadatos de certificados digitales `.p12` usados para
firmar comprobantes electronicos SRI. El certificado representa legalmente al
contribuyente; por eso el sistema nunca debe permitir operar a un tenant con un
certificado que no corresponda a su RUC, tenga clave incorrecta o este caducado.

## Componentes

- Lambda: `backend/lambdas/certificates/`
- Modulo compartido: `backend/shared/certificates/`
- Storage: AWS Secrets Manager
- DynamoDB: tabla `tenants` guarda solo metadatos, nunca bytes del p12 ni password.

## Reglas Contables Y SRI

- El `.p12` debe abrir con la clave ingresada. Si no abre, el registro/cambio de
  certificado se rechaza.
- El certificado debe contener private key; un certificado sin llave privada no puede firmar.
- El RUC extraido del Subject del certificado debe coincidir exactamente con el RUC del
  tenant o del formulario de onboarding.
- Certificados caducados se rechazan con mensaje claro. La fecha de caducidad queda en
  detalle interno/logs; la respuesta HTTP mantiene `AppError.default_message`.
- La clave del certificado nunca se loguea, nunca se devuelve por API y nunca se persiste
  en DynamoDB.
- El endpoint `GET` devuelve solo metadatos.

## Contrato API

| Metodo | Ruta | Auth | Descripcion |
| --- | --- | --- | --- |
| PUT | `/tenants/{id}/certificate` | owner/admin/superadmin | Valida y reemplaza el certificado del tenant |
| GET | `/tenants/{id}/certificate` | owner/admin/viewer/superadmin | Devuelve metadatos del certificado |

### PUT `/tenants/{id}/certificate`

Body:

```json
{
  "certificate_b64": "...",
  "cert_password": "..."
}
```

Reglas:

- `certificate_b64` maximo 50 KB decodificado.
- El RUC del certificado debe coincidir con el RUC del tenant.
- Si es valido, se guarda en Secrets Manager y se actualizan metadatos en `Tenant`.
- Mutacion idempotente con `X-Idempotency-Key`.
- En caso de `OptimisticLockError` al hacer commit, el handler reintenta hasta 3 veces:
  re-obtiene el tenant y reaplica los metadatos ya validados sin repetir la validacion
  del p12 ni el upload a Secrets Manager (`put_certificate` es idempotente por nombre
  determinista de secreto). Detalle del flujo en `ONBOARDING.md`.

### GET `/tenants/{id}/certificate`

Respuesta:

```json
{
  "tenant_id": "uuid",
  "cert_subject_ruc": "179...",
  "cert_expires_at": "2027-01-01T00:00:00+00:00",
  "cert_issuer": "Security Data S.A.",
  "cert_uploaded_at": "2026-06-13T00:00:00+00:00"
}
```

No devuelve `certificate_b64`, password ni ARN interno salvo que exista una necesidad
operativa futura para superadmin.

## Modulo Compartido

`backend/shared/certificates/`:

```text
metadata.py       # CertificateMetadata dataclass
errors.py         # errores de dominio de certificado
validator.py      # parseo p12, RUC, emisor permitido, expiracion
store.py          # Secrets Manager
```

Este modulo se usa desde:

- `onboarding`: validacion inicial antes de enviar OTP y antes de crear tenant.
- `certificates`: reemplazo posterior del certificado.

La logica de parseo y validacion no se duplica entre Lambdas.

## Extraccion De RUC

El campo del RUC varia por CA. El validador debe intentar, en orden:

1. `SERIALNUMBER`
2. `CN` con prefijos tipo `RUC:`
3. cualquier atributo que contenga 13 digitos consecutivos (RUC completo)
4. cualquier atributo que contenga 10 digitos consecutivos (cedula)

Si no puede extraerlo, lanza `CertificateRucNotExtractableError`.

### Personas naturales: p12 con cedula en vez de RUC

En Ecuador una persona natural puede facturar con su propio p12, cuyo Subject
suele contener la **cedula (10 digitos)** en vez del RUC completo (13 digitos).
El RUC de una persona natural es siempre `cedula + "001"` (tercer digito < 6,
ver `shared/domain/value_objects/ecuador_identification.py::is_valid_ruc`).

Por eso el validador acepta el match si:

- el identificador extraido tiene 13 digitos y es igual al RUC esperado, o
- el identificador extraido tiene 10 digitos, es igual a los primeros 10
  digitos del RUC esperado, y el RUC esperado termina en `001`.

En ambos casos `CertificateMetadata.subject_ruc` (y por lo tanto
`tenant.cert_subject_ruc`) se guarda como el **RUC completo de 13 digitos**
(el `expected_ruc`), nunca la cedula de 10 digitos — para que el dato
persistido sea siempre comparable con `tenant.ruc`.

## Errores

- `CERTIFICATE_INVALID`: p12 corrupto, sin private key o clave incorrecta.
- `CERTIFICATE_EXPIRED`: certificado caducado.
- `CERTIFICATE_RUC_MISMATCH`: RUC del certificado distinto al RUC esperado.
- `CERTIFICATE_UNTRUSTED_ISSUER`: emisor no reconocido.
- `CERTIFICATE_RUC_NOT_EXTRACTABLE`: no se pudo extraer RUC del Subject.

## Worker `certificate_expiry_notifier`

- Lambda: `backend/lambdas/workers/certificate_expiry_notifier/` (`handler.py` +
  `use_case.py`), invocada por una regla EventBridge `cron(0 9 * * ? *)` (09:00 UTC /
  04:00 Ecuador), igual en los 3 entornos.
- Umbrales de alerta: `CERTIFICATE_EXPIRY_ALERT_THRESHOLDS_DAYS = (60, 30)` en
  `backend/shared/certificates/expiry.py`. No hay alerta de "ya vencido" — el validador
  ya bloquea esa operacion con `CertificateExpiredError`.
- Flujo: `ITenantRepository.list_with_certificate_expiry_due(before)` escanea tenants
  activos/suspendidos, no eliminados, con `cert_expires_at <= now + 60d`. Para cada
  tenant, `Tenant.due_certificate_expiry_alerts(now)` calcula que umbrales (60, 30)
  aun no se enviaron y ya estan dentro de rango. Por cada umbral pendiente se envia el
  email (`EmailSender.send_certificate_expiry_alert`, implementado en
  `BrevoEmailSender`) y se marca con
  `Tenant.mark_certificate_expiry_alert_sent(threshold, now, updated_by)`.
- Idempotencia entre corridas diarias: el estado "enviado" vive en el propio `Tenant`
  (`cert_expiry_alert_60_sent_at`, `cert_expiry_alert_30_sent_at`), no en una tabla
  aparte. `attach_certificate(...)` resetea ambos campos a `None` — un certificado
  nuevo arranca un ciclo de alertas nuevo.
- Orden deliberado **email primero, persistencia despues**: si el `save()` falla (p.ej.
  `OptimisticLockError`), el peor caso es que la misma alerta se reenvie al dia
  siguiente — aceptable para un recordatorio no critico. El error se loguea como
  warning y no detiene el procesamiento de los demas tenants.
- Persistencia via `ITenantRepository.save(tenant, user_id)` (sin eventos, sin
  idempotencia HTTP — uso interno del worker, `user_id="system:certificate-expiry-notifier"`).

## Costos

Implementacion inicial: Secrets Manager, 1 secreto por tenant.

- Ventaja: cifrado, auditoria, control de acceso e integracion AWS simple.
- Costo: crece linealmente por tenant. Revisar cuando el volumen vuelva relevante el costo
  por secreto mensual.

No usar S3 plano para p12. No usar DynamoDB para bytes/password del certificado.

## Frontend — Gestion Post-Onboarding

Componente compartido `frontend/features/tenants/components/CertificateSection.tsx`,
usado en dos pantallas:

- `TenantDashboardScreen` (owner/admin/viewer de su propio tenant) —
  `tenantId = user.tenantId`, `canManage = canWrite(user.role)`.
- `TenantDetailScreen` (superadmin viendo cualquier tenant) — `tenantId = tenant.id`,
  `canManage = true`.

`canManage` debe coincidir exactamente con los roles permitidos por el backend para
reemplazar certificados (`owner`/`admin`/`superadmin`, ver `PUT` en "Contrato API") —
por eso se usa `canWrite(role)` de `constants/roles.ts`, que cubre el mismo conjunto.

- Datos: `useTenantCertificate(tenantId)` (`GET .../certificate`).
- Reemplazo: `tenantsApi.replaceCertificate(tenantId, {certificate_b64, cert_password},
  idempotencyKey)` (`PUT .../certificate`), con `useFormSubmit` +
  `createIdempotencyKey('certificate_replace')`.
- Selector de archivo `.p12`/`.pfx`: hook compartido
  `frontend/lib/hooks/useCertificateFilePicker.ts` (web-only), tambien usado por
  `RegisterCertificateScreen` del wizard de onboarding.
- Estado de vigencia (`Badge`) calculado en el cliente a partir de `cert_expires_at`:
  vencido → error "Vencido"; ≤30 dias → error "Vence en N dias"; ≤60 dias → warning
  "Vence en N dias"; resto → success "Vigente". Umbrales frontend centralizados en
  `frontend/features/tenants/constants.ts`, alineados con
  `CERTIFICATE_EXPIRY_ALERT_THRESHOLDS_DAYS` del backend — si ese valor cambia, actualizar
  tambien el frontend.

## Decisiones Futuras

- El selector de certificado (`useCertificateFilePicker`, usado por el onboarding y por
  `CertificateSection`) usa input web nativo. Si se habilita onboarding/gestion movil
  nativa, usar `expo-document-picker` dentro de ese mismo hook y mantener el contrato
  base64.
- La whitelist de emisores debe actualizarse cuando aparezcan nuevas CAs reconocidas por SRI.
- Secrets Manager cuesta por secreto/mes. Mantener esta decision mientras el volumen sea
  bajo/medio; re-evaluar Parameter Store SecureString si el costo por tenant se vuelve
  material.

## Deuda Solventada

- 2026-06-14: `GET /tenants/{id}/certificate` permite `viewer` para metadata, mientras
  `PUT` sigue limitado a `owner`/`admin`/`superadmin`.
- 2026-06-14: respuestas de certificado y `Tenant.to_dict()` ya no exponen
  `certificate_secret_arn`.
- 2026-06-14: el worker de expiracion envia `days_remaining` real; ya no usa el umbral
  60/30 como si fueran dias restantes.
- 2026-06-14: umbrales backend viven en `shared/certificates/expiry.py`; umbrales frontend
  viven en `features/tenants/constants.ts`.
- 2026-06-14: la validacion de emisor ya no usa substring. `validator.py` normaliza el
  nombre del emisor y compara contra `ALLOWED_ISSUER_NAMES`, evitando falsos positivos
  como nombres no confiables que solo contienen `"ANF"` dentro de otra palabra.
