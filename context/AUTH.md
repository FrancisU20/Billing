# Auth — Dominio

Estado: implementado.

## Lee Tambien Antes De Empezar

Leer estos archivos en orden antes de escribir codigo en este dominio:

| Archivo | Por que |
| --- | --- |
| `CLAUDE.md` | Reglas no negociables (seguridad, git) |
| `BACKEND.md` | `_base/permissions.py` (`require_role`, `require_superadmin`), contrato HTTP |
| `FRONTEND.md` | Estructura de `features/auth/`, convencion de estado global con Zustand |

## Proposito

Autenticacion y autorizacion del SaaS. El frontend nunca habla con Cognito directamente;
todo el protocolo SRP se ejecuta en Lambda. El resultado es un JWT (ID Token) que
todos los demas Lambdas usan para identificar al caller.

## Componentes

- Lambda: `backend/lambdas/auth/`
- Cognito User Pool (provisionado por CDK)
- Tabla DynamoDB `password-resets` para códigos de recuperación propios: guarda solo hash
  del código, intentos, expiración y TTL.
- El estado de usuario vive en Cognito.

## Frontend

- `frontend/features/auth/store.ts` — estado global de sesion (Zustand): `user`, `idToken`,
  `accessToken`, `refreshToken`, `hydrated`. Unico store global del proyecto (ver `FRONTEND.md`
  → "Estado Global").
- `frontend/features/auth/storage.ts` — persistencia de tokens (`tokenStorage`).
- `frontend/lib/api/client.ts` — adjunta `Authorization: Bearer <id_token>` leyendo el token
  via getter inyectado; si expira y hay `_onRefresh` configurado, refresca antes de reintentar.
- `ChallengeScreen`: si llega sin `session`/`challenge_name`/`username` (params de ruta
  perdidos por reload, deploy a mitad de flujo, o navegacion directa), redirige a
  `Routes.auth.login` en vez de mostrar el error de Cognito. Tambien expone siempre un
  boton "Volver a iniciar sesion" — la sesion de challenge de Cognito expira a los pocos
  minutos (`NotAuthorizedException`), y este boton es la salida unica para cualquier
  estado roto sin tener que mapear cada codigo de error.

## Rutas

Todas son publicas (sin JWT authorizer en API Gateway).

| Metodo | Ruta | Body |
| --- | --- | --- |
| POST | `/auth/login` | `{ "username": "...", "password": "..." }` |
| POST | `/auth/refresh` | `{ "refresh_token": "..." }` |
| POST | `/auth/logout` | `{ "access_token": "..." }` |
| POST | `/auth/challenge` | `{ "session": "...", "challenge_name": "...", "responses": {...} }` |
| POST | `/auth/forgot-password` | `{ "username": "..." }` |
| POST | `/auth/reset-password` | `{ "username": "...", "confirmation_code": "...", "new_password": "..." }` |

## JWT — Estructura Del Token

Se usa el **ID Token**, no el Access Token. El ID Token contiene los custom attributes
necesarios para permisos en todos los Lambdas.

```json
{
  "sub": "cognito-user-uuid",
  "email": "user@empresa.com",
  "custom:tenant_id": "t-uuid",
  "custom:role": "owner | admin | viewer",
  "custom:is_superadmin": "true | false"
}
```

- `custom:tenant_id` esta vacio para superadmin.
- Enviado como `Authorization: Bearer <id_token>`.
- El JWT authorizer de API Gateway valida firma y expiry antes de que llegue al Lambda.

## Roles

| Rol | Scope | Descripcion |
| --- | --- | --- |
| `superadmin` | global | gestiona tenants, plans, y puede actuar sobre cualquier tenant |
| `owner` | tenant | acceso total dentro de su tenant |
| `admin` | tenant | gestion dentro de su tenant |
| `viewer` | tenant | solo lectura dentro de su tenant |

`require_role` y `require_superadmin` estan en `_base/permissions.py`.

## Flujos

### Login Normal

```
POST /auth/login { username, password }
-> Lambda ejecuta USER_SRP_AUTH contra Cognito
-> Si ok: { access_token, id_token, refresh_token }
-> Si NEW_PASSWORD_REQUIRED: { session, challenge_name, parameters: { username, ... } }
```

### Cambio De Clave Obligatorio (onboarding)

```
POST /auth/challenge {
  session, challenge_name: "NEW_PASSWORD_REQUIRED",
  responses: { NEW_PASSWORD: "...", USERNAME: "..." }
}
-> Cognito acepta la nueva clave
-> Respuesta: { access_token, id_token, refresh_token }
```

Este challenge ocurre la primera vez que un tenant entra con su clave temporal
generada por `AdminCreateUser` durante el onboarding.

**`USERNAME` en `responses` debe ser el `USER_ID_FOR_SRP`** (sub interno del User
Pool), no el alias de email usado para el login — el pool usa
`sign_in_aliases.email=True` con `username` autogenerado, y Cognito rechaza
`RespondToAuthChallenge` con `InvalidParameterException` si `USERNAME` no coincide
con el `USER_ID_FOR_SRP` del paso SRP inicial. La respuesta NEW_PASSWORD_REQUIRED
encadenada (tras `PASSWORD_VERIFIER`) no repite `USER_ID_FOR_SRP` en sus propias
`ChallengeParameters`, por lo que `CognitoAuthProvider.login` lo copia
manualmente del `init_response` antes de mapear `parameters.username` (ver
`infra/cognito_auth_provider.py`). El frontend reenvia ese `parameters.username`
tal cual en `responses.USERNAME`.

### Refresh

```
POST /auth/refresh { refresh_token }
-> Cognito emite nuevos access_token e id_token
-> El refresh_token puede o no rotar segun config del User Pool
```

### Olvidé Mi Contraseña (agregado 2026-06-21)

Hasta esta fecha no existía ningún mecanismo de recuperación de contraseña — un usuario
que olvidaba su clave (o no recibía el email de bienvenida por algún motivo) quedaba sin
salida. Desde 2026-06-24 el flujo no usa el canal de email de Cognito: Wali genera el
código, guarda su hash en DynamoDB y lo envía por `email_notifications`/Brevo.

```
POST /auth/forgot-password { username }
-> Cognito AdminGetUser valida si existe el usuario. Si no existe, no se crea código ni
   se envía correo.
-> Si existe: se genera código de 6 dígitos, se guarda hash PBKDF2 + salt en
   `password-resets` con TTL 15 min e intentos máximos 5.
-> Se publica `PasswordResetRequestedEvent` directo a la cola `email_notifications`.
-> `email_notifications` envía plantilla Wali por Brevo desde `no-reply@codelabsecuador.com`
   (en ambientes no-prod el sender real se fuerza a `testing@codelabsecuador.com`).
-> Respuesta SIEMPRE genérica: { "message": "Si el correo está registrado, te
   enviamos un código de recuperación." } — incluso si el username no existe
   (`user_exists=False` corta silenciosamente). Nunca reveles si una cuenta existe — el
   frontend tampoco se entera, navega igual al siguiente paso.

POST /auth/reset-password { username, confirmation_code, new_password }
-> Lee `password-resets` por username, valida que no esté expirado/usado/bloqueado y
   compara el código contra el hash.
-> Código inválido incrementa intentos y responde `INVALID_CHALLENGE_RESPONSE`.
-> Código válido llama `AdminSetUserPassword(Permanent=True)` en Cognito y marca el reset
   como usado.
-> 204 en éxito; contraseña inválida por política Cognito se mapea a
   `INVALID_CHALLENGE_RESPONSE`.
```

Frontend: `ForgotPasswordScreen` (`/(auth)/forgot-password`, link "¿Olvidaste tu
contraseña?" desde `LoginScreen`) → siempre navega a `ResetPasswordScreen`
(`/(auth)/reset-password?username=...`) sin importar la respuesta del backend → en
éxito, `router.replace(Routes.auth.login)`. También enlazado desde
`RegistrationForm` (dominio `onboarding`) cuando el registro falla con
`TENANT_ACCOUNT_ALREADY_EXISTS` — ese error ahora ofrece "Iniciar sesión" y
"¿Olvidaste tu contraseña?" en vez de ser un callejón sin salida (ver
`ONBOARDING.md` → "Fase 4").

`POST /auth/forgot-password` tiene throttle propio (`api.throttling.auth_forgot_password`
en `infra/config/*.yaml`, burst 5/rate 1 — mismo perfil que `onboarding_otp_request`) por
ser una ruta pública propensa a abuso/enumeración. `reset-password` no lo necesita — ya
requiere conocer el código correcto.

## Reglas

- Nunca devolver secrets de challenge SRP del lado servidor: `SALT`, `SRP_B`, `SECRET_BLOCK`.
- `logout` llama `GlobalSignOut`; si el token ya expiro o es invalido, responder exito
  igualmente (best-effort).
- El SRP se implementa en `auth/infra/srp.py`. No mover logica SRP al frontend.

## Edge Cases Y Trampas

- **Test de superadmin que recibe 401 en lugar de 403**: el parser de `_base/parser.py:98`
  lanza `MissingTenantContextError` (401) cuando `is_superadmin=False` y `tenant_id` esta
  vacio. En tests de permisos superadmin, siempre incluir `"custom:tenant_id": "t1"` en los
  claims aunque no se use, para no confundir 401 con 403.

- **Cognito no es transaccional**: si el worker `tenant_onboarding` crea el usuario Cognito
  pero DynamoDB ya fallo antes, el usuario queda huerfano. El mecanismo de recuperacion es
  re-encolar el evento de onboarding (idempotente por diseno).

## Memberships / Multi-Tenant Switch — Futuro (Pendiente)

Hoy `custom:tenant_id` es singular: un usuario Cognito pertenece a un solo tenant. El
onboarding (ver `ONBOARDING.md`) refuerza esto — un email = un tenant, sin logica especial
de email compartido.

Caso real no resuelto: un contador administra varios RUCs (tenants) y no deberia necesitar
un login distinto por cada uno.

Diseno futuro (no implementar como parte de onboarding):

- Tabla de membresias `(user_sub, tenant_id, role)` — relacion N:M, separada de los custom
  attributes de Cognito (que son de un solo valor).
- `POST /auth/switch-tenant { tenant_id }` — valida que `user_sub` tenga membresia en ese
  `tenant_id` y re-emite JWT con `custom:tenant_id` actualizado.
- Compatible hacia atras: el modelo actual (un owner por tenant creado en onboarding) se
  modela como una membresia con `role=owner` — no requiere migrar tenants existentes,
  solo poblar la tabla de membresias con una fila por tenant al momento de implementarlo.

## Deuda Tecnica

- No hay tests de integracion contra Cognito real; los tests usan fakes.
- El token refresh no rota el refresh_token actualmente; evaluar si el User Pool debe tener
  rotacion activada para mayor seguridad.
