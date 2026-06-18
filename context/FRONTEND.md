# Frontend — Arquitectura Y Patrones

Patrones de construccion transversales: estructura de carpetas, design system, componentes
compartidos, routing y convenciones de pantallas. Las reglas de negocio especificas de cada
dominio (que pantallas existen, hooks de ese dominio, reglas de UI propias) viven en la
seccion "Frontend" de cada archivo de dominio (`AUTH.md`, `TENANTS.md`, `PLANS.md`,
`CLIENTS.md`, `ONBOARDING.md`).

## Estructura

```text
frontend/
  app/                      # Expo Router: rutas por archivos
    (public)/                # rutas publicas, sin login
    (auth)/                  # login, challenge MFA
    (app)/                   # rutas autenticadas
      (tenant)/               # owner/admin/viewer — scoped a su tenant
      (superadmin)/           # superadmin — gestion global
  components/
    ui/                      # primitivas compartidas (Button, Card, Input, ...)
    feedback/                # Toast y feedback global
    layout/                  # Screen, NavBar
  constants/                 # routes, tokens, roles, config
  features/{area}/
    api.ts                   # llamadas HTTP + validacion Zod
    schemas.ts               # Zod schemas
    types.ts                 # tipos derivados de schemas
    constants.ts             # opciones de filtro, enums de UI
    form.ts                  # mapeo form values <-> DTO API
    hooks/
    components/
    screens/
  lib/
    api/                     # client, errors, idempotency, types
    hooks/                   # useAsync, useFetch, usePaginatedList
    theme-context.tsx        # design system activo (ver "Design System")
    utils/                   # format, jwt
```

Features actuales: `auth`, `marketing`, `onboarding`, `tenants`, `plans`, `clients`,
`products`, `documents`, `sequences`, `subscriptions`, `navigation` y `design-system`.

## Design System

Todo el theming vive en `constants/tokens.ts` + `lib/theme-context.tsx`. **Nunca**
hardcodear colores, spacing, radius o tipografia en un componente.

### Tokens (`constants/tokens.ts`)

| Token                            | Uso                                                                                                                                                            |
| -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `colors`                         | paleta cruda (primary, cyan, teal, neutral, success, warning, error). No usar directo en pantallas — usar `semantic`.                                          |
| `lightSemantic` / `darkSemantic` | tokens semanticos por tema: `bg`, `text`, `border`, `accent`, `chart`, `status`                                                                                |
| `spacing`                        | escala 0–20 (4px base)                                                                                                                                         |
| `sizes`                          | dimensiones fijas reutilizables: `icon` (contenedores de icono en secciones/metricas), `avatarSm`/`avatarMd`/`avatarLg` (avatares de listas/detalle/dashboard) |
| `radius`                         | `none` a `full`                                                                                                                                                |
| `typography`                     | `fontFamily`, `size`, `weight`, `lineHeight`                                                                                                                   |
| `shadow`                         | `sm`/`md`/`lg`/`xl`, usa `boxShadow` (valido en Expo Web, fuera del tipo `ViewStyle` de RN)                                                                    |
| `overlay`                        | texto/borde/superficie para zonas siempre oscuras (nav, cards highlighted), independiente del tema                                                             |
| `animation`                      | duraciones estandar                                                                                                                                            |

### Tema (`lib/theme-context.tsx`)

```ts
const { semantic, isDark, colorScheme } = useTheme();
```

- `semantic` cambia automaticamente segun `useColorScheme()` (light/dark).
- Componentes aplican color via `style={[styles.x, { color: semantic.text.primary }]}`.
- Componentes nuevos usan `useTheme().semantic`, no imports directos de tokens
  semanticos por tema.

### Branding E Iconos

Los iconos de aplicacion y favicons se generan desde `frontend/scripts/brand-assets.mjs`.
No editar manualmente `assets/icon.png`, `assets/favicon.png`, `public/favicon.png`,
`public/favicon-light.svg` ni `public/favicon-dark.svg`.

Comandos:

```bash
npm run brand:generate  # regenera SVG/PNG desde la definicion canonica
npm run brand:verify    # valida SVG, dimensiones PNG y que Expo no inyecte favicon alterno
```

`npm run build:web` ejecuta `brand:verify` antes de exportar. `app.json` no debe definir
`expo.web.favicon`; los favicons web se declaran explicitamente en `app/+html.tsx` para
evitar assets competidores.

## Componentes Compartidos

No crear un componente nuevo si uno de estos cubre el caso. Antes de agregar a
`components/ui/`, confirmar que es realmente transversal (2+ features lo necesitan);
si es especifico de un dominio, va en `features/{area}/components/`.

`components/ui/`:

| Componente                   | Uso                                                                                                                                                                                                                 |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Button.tsx`                 | botones primarios/secundarios                                                                                                                                                                                       |
| `Input.tsx`, `FormField.tsx` | campos de formulario + label/error                                                                                                                                                                                  |
| `Card.tsx`                   | contenedor con elevacion                                                                                                                                                                                            |
| `Badge.tsx`                  | etiquetas de estado                                                                                                                                                                                                 |
| `ListItemPrimitives.tsx`     | `ListItemAction`, `ListItemMeta` y piezas de filas de listado                                                                                                                                                       |
| `LoadingSpinner.tsx`         | spinner full-screen o inline                                                                                                                                                                                        |
| `EmptyState.tsx`             | estado vacio con icono + accion                                                                                                                                                                                     |
| `ApiErrorBanner.tsx`         | banner de error de API                                                                                                                                                                                              |
| `ConfirmDialog.tsx`          | confirmacion de acciones destructivas/irreversibles                                                                                                                                                                 |
| `SegmentedControl.tsx`       | selector tipo tabs                                                                                                                                                                                                  |
| `Divider.tsx`                | separador                                                                                                                                                                                                           |
| `DetailSection.tsx`          | `DetailSection`/`DetailField` — seccion con titulo+icono y grupo de pares label/valor en pantallas de detalle (`layout="grid"` por defecto, `"stack"` para apilar verticalmente, ej. bloques con botones de accion) |
| `StatMetric.tsx`             | tarjeta de metrica (icono + valor + label) para resumenes/dashboards                                                                                                                                                |
| `CertificateUploadField.tsx` | selector de archivo p12 + clave (Pressable de carga + `FormField` de password + error). Usar junto a `useCertificateFilePicker` (`lib/hooks/`). Compartido por onboarding (wizard) y tenants (reemplazo de certificado).                                          |

`components/feedback/`:

| Componente  | Uso                                                     |
| ----------- | ------------------------------------------------------- |
| `Toast.tsx` | `useToast()` — `toast.success(...)`, `toast.error(...)` |

`components/layout/`:

| Componente   | Uso                                                                                                                                                                                                                                                               |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Screen.tsx` | wrapper de pantalla: `SafeAreaView` + bg + padding + scroll/keyboard opcional                                                                                                                                                                                     |
| `NavBar.tsx` | primitiva de barra superior: titulo, `canGoBack`, `NavIconButton`. No usar directo en pantallas autenticadas — ver `AppNavBar` abajo. `NavIconButton` siempre lleva `accessibilityRole="button"` y `accessibilityLabel` descriptivo (ej. "Volver", "Abrir menú"). |

`features/navigation/` (no es `components/`, pero es transversal a todas las pantallas autenticadas):

| Archivo                                                                                 | Uso                                                                                                                                                                                                                |
| --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `components/AppNavBar.tsx`                                                              | envuelve `NavBar` y agrega menu hamburguesa (`NavigationMenu`) + menu de cuenta (`AccountMenu`/`UserAvatar`) segun `useAuthStore`. **Esta es la barra que usan las pantallas de `(app)/**`**, no `NavBar` directo. |
| `components/NavigationMenu.tsx`, `AccountMenu.tsx`, `MenuSurface.tsx`, `UserAvatar.tsx` | piezas internas de `AppNavBar`                                                                                                                                                                                     |
| `items.ts`                                                                              | items del menu de navegacion                                                                                                                                                                                       |

## Marketing Y Paginas Legales

`features/marketing/` contiene el landing publico (`LandingScreen` +
`HeroSection`/`FeaturesSection`/`HowItWorksSection`/`PlansSection`/`LandingHeader`/`LandingFooter`)
y las paginas legales:

- `content/legal.ts` — contenido tipado (`LegalContent`/`LegalSection`/`LegalBlock`: parrafos
  `{ type: 'p' }` o listas `{ type: 'list' }`), separado de la presentacion. Email de contacto
  centralizado ahi (`CONTACT_EMAIL = ventas@codelabsecuador.com`).
- `components/LegalPageLayout.tsx` — layout unico (reusa `LandingHeader`/`LandingFooter`, hero
  oscuro con `colors.nav`) para cualquier pagina legal. Para agregar una pagina legal nueva:
  agregar su `LegalContent` en `content/legal.ts`, un screen trivial que pase ese contenido al
  layout, ruta en `Routes.public.legal*` y archivo en `app/(public)/legal/`.
- Rutas: `Routes.public.legalTerms`, `legalPrivacy`, `legalRefund` →
  `/legal/terms`, `/legal/privacy`, `/legal/refund`. Linkeadas desde `LandingFooter` (visibles en
  toda la app).

Nota: el export web (`expo export --platform web`) es CSR puro — el HTML inicial no contiene el
contenido de estas paginas ni de `PlansSection`. Si un crawler que no ejecuta JS necesita ver ese
contenido (ej. verificacion de una pasarela de pagos), evaluar SSG/prerender para `(public)` como
tarea aparte.

## Routing (Expo Router)

Grupos de rutas en `app/`:

| Grupo                | Acceso             | Contenido                       |
| -------------------- | ------------------ | ------------------------------- |
| `(public)`           | sin login          | landing, pricing                |
| `(auth)`             | sin login          | login, challenge MFA            |
| `(app)`              | autenticado        | layout comun (`profile`)        |
| `(app)/(tenant)`     | owner/admin/viewer | dashboard, clients              |
| `(app)/(superadmin)` | superadmin         | tenants, plans (gestion global) |

Reglas:

- Los segmentos de URL y archivos bajo `app/` van siempre en ingles (`/components`,
  `/clients`, `/register/details`). El texto visible de la UI puede estar en espanol.
- Archivos en `app/` son **siempre** re-exports de 2 lineas de un screen en
  `features/{area}/screens/`, sin excepcion:
  ```tsx
  import { XScreen } from "@/features/{area}/screens/XScreen";
  export default XScreen;
  ```
  No implementar logica/JSX de pantalla directo en `app/`.
- Excepcion al patron anterior: archivos especiales de Expo Router con prefijo `+`
  (`app/+html.tsx`, y si se agrega en el futuro `app/+not-found.tsx`). No son rutas de
  features, sino hooks del framework (documento HTML raiz para web, pantalla 404, etc.)
  y por eso viven con su logica/JSX completo directo en `app/`, sin re-export.
- Todas las rutas se referencian via `constants/routes.ts` (`Routes.superadmin.tenantDetail(id)`,
  etc.). Nunca strings de ruta sueltos en pantallas/componentes.
- Rutas con parametros son funciones (`(id: string) => ...`), no templates inline.
- Si una pantalla requiere un rol especifico, va en el grupo correspondiente
  (`(tenant)` vs `(superadmin)`) — no condicionar visibilidad solo en el componente.

## Patrones De Pantalla

Toda pantalla autenticada sigue esta forma (ver `tenants/new.tsx` como referencia):

```tsx
export default function XScreen() {
  const { semantic } = useTheme()
  const { data, loading, error, refresh } = useXyz()

  if (loading) return <LoadingSpinner fullScreen label="Cargando..." />

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <AppNavBar title="..." canGoBack />
      {error ? (
        <ApiErrorBanner error={error} />
      ) : data.length === 0 ? (
        <EmptyState icon="..." title="..." description="..." action={{ label: 'Reintentar', onPress: refresh }} />
      ) : (
        /* contenido */
      )}
    </View>
  )
}
```

Pantallas de detalle (`use{Entity}` con `{ data, loading, error, refresh }` para un solo
recurso) usan `EmptyState` tambien para el estado de error, con `refresh` como retry:

```tsx
{error ? (
  <EmptyState
    icon="alert-circle-outline"
    title="No se pudo cargar ..."
    description={error.message}
    action={{ label: 'Reintentar', onPress: refresh }}
  />
) : (
  <>
    {actionError ? <ApiErrorBanner error={actionError} /> : null}
    {data ? /* contenido */ : null}
  </>
)}
```

`useFetch` siempre deja `data: null` cuando `error` esta seteado, por lo que `error` solo
ya cubre el caso "sin datos que mostrar" — no hace falta `error && !data`.

Reglas:

- Loading → `LoadingSpinner fullScreen`. Error → `ApiErrorBanner` (listas) o `EmptyState`
  con retry (detalle). Vacio → `EmptyState` con accion de retry. Nunca dejar una pantalla
  en blanco silenciosa.
- Usar `Screen` (de `components/layout`) cuando la pantalla no necesita el patron
  hero/list custom — evita repetir `SafeAreaView` + `StyleSheet` boilerplate.
- Estilos con `StyleSheet.create`, valores de color/spacing siempre desde `semantic`/`tokens`,
  nunca numeros o hex sueltos.

## Hooks Reutilizables (`lib/hooks/`)

| Hook                                        | Uso                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `useAsync`                                  | ejecutar una promesa con estados loading/error                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `useFetch<T>(fetcher)`                      | fetch de un solo recurso: recibe `(() => Promise<T>) \| null` (null = no fetchear) y devuelve `{ data, loading, error, refresh }`. `fetcher` debe ser estable (`useCallback`) para evitar loops. Base de los hooks `use{Entity}` por dominio (`useClient`, `useTenant`, `usePlan`, `useAdminPlan`).                                                                                                                                                                      |
| `usePaginatedList<T, F>(filters, loadPage)` | listas paginadas: `items`, `nextToken`, `hasMore`, `loading`, `loadingMore`, `error`, `refresh`, `fetchMore`. No llamar `fetchMore` mientras `loading` o `loadingMore` esten activos — el hook ya lo bloquea internamente.                                                                                                                                                                                                                                               |
| `useFormSubmit<TArgs>(action)`              | analogo de escritura a `useFetch`: envuelve una accion async (crear/actualizar/cambiar estado/borrar) con `submitting`/`error` + el try/catch/finally + `toApiError` estandar. Devuelve `{ submitting, error, submit }`, donde `submit` es `(...args: TArgs) => Promise<void>` (asignable a props `onPress`/`onConfirm`/`onSubmit` con retorno `void`). Usar siempre que una pantalla haga un submit/accion con loading+error, en vez de repetir `useState` + try/catch. |
| `useCertificateFilePicker(init?)`           | selector de archivo `.p12`/`.pfx` (web-only): devuelve `{ fileName, certificateB64, error, pickFile, reset }`. Usado por `RegisterCertificateScreen` (onboarding) y `CertificateSection` (gestion post-onboarding, ver `ONBOARDING.md`/`CERTIFICATES.md`). |

## Estado Global

La mayoria de features no necesitan estado global: datos de servidor se manejan con
`usePaginatedList`/`useAsync` por pantalla. Cuando si hace falta estado compartido entre
features (ej. sesion de auth en `features/auth/store.ts`), usar **Zustand** — ya es
dependencia del proyecto. No introducir Context API ni otra libreria de estado para esto.

## Reglas Generales

- Validar respuestas con Zod en `api.ts`.
- Mantener `types.ts` derivados de `schemas.ts` cuando aplique.
- Schema de validacion de formularios (`*FormValuesSchema` + tipo `*FormValues`) vive en
  `features/{area}/schemas.ts`, no inline en el componente `*Form.tsx`. El componente
  importa el schema y lo pasa a `zodResolver(...)`. Ver `clientFormValuesSchema`,
  `tenantFormValuesSchema`, `planFormValuesSchema`.
- No duplicar hooks de fetch/paginacion: `useFetch` para un solo recurso, `usePaginatedList`
  para listas.
- No duplicar el patron submit/accion con loading+error: usar `useFormSubmit` (ver
  `lib/hooks/useFormSubmit.ts`) en pantallas de creacion/edicion y en acciones de
  detalle/listado (toggle, delete, cambio de estado).
- No duplicar acciones/metadatos de filas; usar `ListItemAction` y `ListItemMeta`.
- Para filtros, separar draft UI de filtros aplicados (`draft` vs `filters`).
- Evitar objetos inline como filtros permanentes si un hook depende de ellos.
  Usar constantes estables o memoizar con `useCallback`/`useMemo`.
- Las metricas en listados cuentan items cargados, no totales reales.
  Para dashboards usar endpoint agregado backend.

## Notas Expo

**Expo HAS CHANGED.** Antes de escribir codigo que dependa de comportamiento de
Expo Router / Expo SDK, leer la documentacion versionada exacta de v56 en
https://docs.expo.dev/versions/v56.0.0/ — no asumir comportamiento de versiones previas.

- `expo-env.d.ts` esta gitignored; CI puede no cargar augmentations de `expo/types`.
- Al componer `Pressable` con callback style, pasar `state` completo o asumir
  solo `{ pressed: boolean }`.
- iOS Safari hace autozoom al enfocar cualquier `input`/`textarea` con
  `font-size` calculado < 16px. `Input.tsx` (`webTextInputReset`) fuerza
  `fontSize: typography.size.md` (16) solo en `Platform.OS === 'web'`. Si se
  crea otro campo de texto web fuera de `Input.tsx`, aplicar el mismo minimo.

## Como Agregar Un Feature Frontend

**Paso 0 — Leer antes de escribir codigo:**

- `CLAUDE.md` — reglas no negociables.
- `FRONTEND.md` (este archivo) — patrones de construccion.
- La seccion "Frontend" del archivo de dominio correspondiente (ej. `TENANTS.md`).

**Pasos de implementacion:**

1. Definir Zod schemas en `features/{area}/schemas.ts`.
2. Exportar tipos desde `types.ts`.
3. Implementar `api.ts` con validacion de respuesta.
4. Usar hooks existentes (`useAsync`, `useFetch`, `usePaginatedList`) antes de crear uno nuevo.
5. Reusar `components/ui` / `components/layout` antes de crear un componente nuevo;
   si es especifico del dominio, va en `features/{area}/components/`.
6. Mantener pantallas como composicion de componentes, siguiendo el patron
   loading/error/empty de "Patrones De Pantalla".
7. Registrar rutas nuevas en `constants/routes.ts`.
8. Correr `typecheck`, `lint` y tests.

## Comandos Frontend

```bash
cd frontend
npm run format:check
npm run typecheck
npm run lint
npm run test:run
npm run build:web
```

## Calidad Esperada

- Un solo design system: cero colores/spacing hardcodeados fuera de `tokens.ts`.
- Un solo patron de pantalla (loading/error/empty); no inventar variantes por feature.
- No crear hooks o componentes "casi iguales" a uno existente — extender o reusar.
- No hacer refactors grandes sin necesidad; extraer solo cuando elimina duplicacion real.
- Tests deben cubrir reglas nuevas y bugs corregidos.

## Decisiones Futuras

- `useCertificateFilePicker` es web-only. Si se habilita experiencia movil nativa para
  onboarding o reemplazo de certificados, implementar `expo-document-picker` dentro del
  mismo hook manteniendo el contrato `{ certificateB64, fileName }`.

## Deuda Solventada

- 2026-06-14: los umbrales de estado de certificado en UI viven en
  `features/tenants/constants.ts` y se reutilizan desde `CertificateSection`.
- 2026-06-14: `otpRequestIdempotencyKey` rota luego de solicitar un OTP, evitando que
  volver al paso anterior reutilice una respuesta cacheada.
- 2026-06-14: se elimino el alias legacy `semantic` exportado desde
  `constants/tokens.ts`; no quedaban imports directos y el acceso semantico queda
  centralizado en `useTheme().semantic`.

## Tests De Hooks

`vitest.config.ts` usa `environment: 'node'` por defecto. Para tests de hooks que
necesiten `renderHook`/`waitFor` de `@testing-library/react` (entorno DOM), agregar
al inicio del archivo:

```ts
// @vitest-environment jsdom
import { renderHook, waitFor } from "@testing-library/react";
```

Reglas:

- Mocks de modulo (`vi.mock('../api', ...)`) con `vi.fn()` a nivel de modulo: resetear
  con `mock.mockReset()` en `beforeEach` para evitar fugas de call-count entre `it()`.
- Si un hook depende de un objeto/array como `useCallback`/`useEffect` dep (ej. `filters`
  en `useAdminPlans`), usar una referencia estable (`const filters = {...}` fuera del
  callback de `renderHook`) — un literal inline en cada render causa loop infinito.
- Ver `lib/hooks/useFetch.test.ts`, `features/clients/hooks/useClient.test.ts`,
  `features/plans/hooks/usePlans.test.ts` como referencia.
- Para hooks de `features/auth/` que dependen de `../store` (Zustand + `expo-secure-store`),
  mockear el modulo `../store` completo con `vi.mock(...)` para evitar resolver dependencias
  de Expo en jsdom. Ver `features/auth/hooks/useLogin.test.ts`, `useChallenge.test.ts`,
  `useLogout.test.ts`.
