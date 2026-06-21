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
    hooks/                   # useAsync, useFetch, useCursorPagedList
    theme-context.tsx        # design system activo (ver "Design System")
    utils/                   # format, jwt
```

Features actuales: `auth`, `marketing`, `onboarding`, `tenants`, `plans`, `clients`,
`products`, `documents`, `sequences`, `subscriptions`, `navigation` y `design-system`.

## Design System

Todo el theming vive en `constants/tokens.ts` + `lib/theme-context.tsx`. **Nunca**
hardcodear colores, spacing, radius o tipografia en un componente.

Direccion visual vigente (refresh 2026-06-20): app SaaS operacional, limpia y densa.
Priorizar superficies blancas/slate, bordes sutiles, radios moderados (cards de 8px por
defecto), primary blue + info cyan + success green balanceados y jerarquia tipografica compacta. Evitar
gradientes decorativos, cards anidadas, fondos monocromaticos morados y sombras pesadas
en pantallas de trabajo.

### Tokens (`constants/tokens.ts`)

| Token                            | Uso                                                                                                                                                            |
| -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `colors`                         | paleta cruda aprobada (primary, cyan/info, neutral/slate, success, warning, error). No usar directo en pantallas — usar `semantic`.                            |
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

Regla permanente: listados, busquedas, filtros, calendarios, formularios, acciones de
estado, modales y consistencia visual de descuentos nacen compartidos salvo justificacion
explicita (2+ features los necesitan). El alcance es toda la app: tenant, superadmin,
auth/onboarding y modulos futuros. Esta regla viene del UX Refactor & Operability Roadmap
(sprints 0-7, completado — ver `CLAUDE.md` "Estado Actual"), que ya cumplio su proposito y
no se mantiene como documento aparte; lo que quedo pendiente vive en `## Deuda Tecnica`
abajo.

`components/ui/`:

| Componente                   | Uso                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `Button.tsx`                 | botones primarios/secundarios                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| `Input.tsx`, `FormField.tsx` | campos de formulario + label/error. `isDisabled` (campo bloqueado, no input vacio): atenua opacidad, muestra icono de candado a la derecha (salvo `secureTextEntry`/`rightElement` explicito) y en web bloquea el foco/caret con `pointerEvents="none"` + `cursor: not-allowed` — sin esto el campo se ve "clickeable" (caret titilando) aunque `editable={false}` ya bloquee la escritura. Tratamiento centralizado en `Input.tsx`, aplica a todo campo `isDisabled` de la app (no solo Comprador en documentos).                                                                                                                                                                                                                               |
| `SpecializedFields.tsx`      | wrappers de `FormField` para campos repetidos (`EmailField`, `RucField`, `IdentificationField`, `MoneyField`, `PercentField`, `PhoneField`) con teclado/icono/autocap/maxLength centralizados. Usar junto a schemas Zod y `mode: "onChange"` para validacion en vivo.                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `FormActions.tsx`            | bloque compartido de acciones de formulario: submit primario, loading, disabled por validacion local, hint de campos pendientes y cancel opcional. Usar en formularios CRUD/wizard en lugar de botones finales sueltos.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `SearchInput.tsx`            | campo de busqueda compartido con icono, limpiar, debounce, minimo de caracteres y hint. Usar para busquedas remotas en listados y pickers; no llamar backend con 1-2 caracteres.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `DateRangePicker.tsx`        | selector compartido de rango de fechas para filtros de listado. Modal RN/Web con calendario, presets Hoy/Esta semana/Este mes/Limpiar, rango ordenado y salida civil `YYYY-MM-DD`. No usar inputs manuales `Desde/Hasta` en listados.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `Card.tsx`                   | contenedor con elevacion                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `Badge.tsx`                  | etiquetas de estado                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `ListItemPrimitives.tsx`     | `ListItemAction` (boton de accion de fila), `ListItemMeta` (chip icono+texto, variante mobile apilada), `ListCell` (columna "label arriba, valor abajo" para la variante desktop de filas de listado — el ancho de columna se pasa via `style`) y `EntityAvatar` (circulo con iniciales o icono fijo para la primera columna de una fila).                                                                                                                                                                                                                                                                                                                                                                                                       |
| `RowActionsMenu.tsx`         | **Estandar de acciones de fila en listados**: boton de ojo (`ListItemAction icon="eye-outline"`, accion "Ver", siempre visible y aparte) + `RowActionsMenu` (icono `ellipsis-vertical`, abre un action sheet con el resto de acciones — `RowAction[]`: `key`, `icon`, `label`, `danger?`, `onPress`). Si `actions` queda vacio no renderiza nada (no hay un kebab vacio). Usar en TODA fila de listado con mas de la accion "Ver" — no agregar botones planos sueltos por cada accion (ver `PlanListItem`/`ClientListItem`/`ProductListItem`/`TenantListItem`/`DocumentListItem`).                                                                                                                                                               |
| `LoadingSpinner.tsx`         | spinner full-screen o inline                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| `EmptyState.tsx`             | estado vacio con icono + accion                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `ApiErrorBanner.tsx`         | banner de error de API                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `ConfirmDialog.tsx`          | confirmacion de acciones destructivas/irreversibles                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `SegmentedControl.tsx`       | selector tipo tabs. Por defecto ancho segun contenido (`alignSelf: 'flex-start'`) para usos inline en formularios. `stretch?: boolean` reparte el ancho disponible en partes iguales entre las opciones — usar dentro de `FilterBlock` en paneles de filtros (`TenantsFilters`/`PlansFilters`) para que el control aproveche el ancho de su columna en vez de quedar angosto con espacio vacio al lado. `columns?: number` (junto a `stretch`) fuerza N opciones por fila via `minWidth` porcentual — usar cuando opciones de texto corto (ej. "RUC"/"Cédula") envolverian de forma dispareja con `flexWrap` solo (3 en la primera fila, 1 sola en la segunda); ver `ClientPickerModal` (creacion rapida, tipo de identificacion en grilla 2x2). |
| `Divider.tsx`                | separador                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `DetailSection.tsx`          | `DetailSection`/`DetailField` — seccion con titulo+icono y grupo de pares label/valor en pantallas de detalle (`layout="grid"` por defecto, `"stack"` para apilar verticalmente, ej. bloques con botones de accion)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| `DetailHeader.tsx`           | encabezado compartido de pantallas de detalle: avatar/icono, titulo, subtitulo/eyebrow, badges y acciones. Usar para detalles de entidades con acciones principales (`Editar`, `Eliminar`) en lugar de rearmar headers locales por feature.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| `StatMetric.tsx`             | tarjeta de metrica (icono + valor + label) para resumenes/dashboards. `value` acepta `number` (conteos) o `string` ya formateado (ej. `formatCurrency(...)` para montos). `trend?: { pct, label }` opcional agrega flecha+texto verde/rojo debajo del valor — omitir el prop entero (no pasar `pct` con un valor inventado) cuando el backend no puede comparar honestamente contra un periodo anterior. `size?: 'md' \| 'lg'` (default `'md'`) — `'lg'` agranda icono/padding/valor para metricas destacadas (ej. fila de ingresos/MRR del dashboard superadmin).                                                                                                                                                                               |
| `ListPaginationControls.tsx` | controles compartidos de listados operativos: pagina actual, selector 10/25/50, anterior/siguiente. Acepta `totalItems`/`totalPages` opcionales — cuando el backend los expone muestra "Pagina X de Y" + total real; si no (filtro de texto libre activo), cae a "Pagina X" + conteo de la pagina actual. Acepta `onGoToPage?: (page: number) => void` opcional — cuando esta presente y hay mas de 2 paginas (`totalPages > 2` con total conocido) muestra `PageJumpControl` (input numerico + boton) para saltar directo a una pagina; el clamp de rango lo hace el hook (`goToPage` de `useLocalPagedItems`/`useEagerPagedList`), no el componente.                                                                                           |
| `CertificateUploadField.tsx` | selector de archivo p12 + clave (Pressable de carga + `FormField` de password + error). Usar junto a `useCertificateFilePicker` (`lib/hooks/`). Compartido por onboarding (wizard) y tenants (reemplazo de certificado).                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `FilterBar.tsx`              | filtros principales siempre visibles (children) + filtros secundarios colapsados detras de "Mas filtros" (con badge de cantidad activa) + chips de filtros activos con `x` para quitar uno y aplicar de inmediato + par de botones "Limpiar"/"Aplicar" juntos al pie del panel expandido (no hay accion de reset suelta en una esquina). Usar para cualquier panel de filtros con mas de 1-2 campos secundarios (status/tipo/fechas); no envolver un filtro que ya es minimo (ej. un solo segmented control).                                                                                                                                                                                                                                    |
| `FilterBlock.tsx`            | `FilterBlock` (label + contenido) — layout del contenido secundario de `FilterBar`. Las opciones seleccionables van con `SegmentedControl`, no con pills sueltas (`FilterPill` se elimino, quedo sin consumidores tras migrar todos los filtros a `SegmentedControl`).                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `PickerModal.tsx`            | esqueleto compartido de modales "buscar y seleccionar": overlay + dialog + header con cerrar + `SearchInput` (busqueda reactiva mientras se escribe, sin boton "Buscar" — Enter en el input dispara `onSearchSubmit` igual) + `ApiErrorBanner` + `FlatList` con estado vacio parametrizable, mas slots opcionales `headerActions` (boton extra junto a la barra de busqueda, ej. "Añadir") y `footer` (bloque debajo de la lista, ej. creacion rapida). `PickerResultRow` es el wrapper presionable para cada fila de resultado. Usado por `ClientPickerModal` (documents) y `ProductPickerModal` (products) como wrappers delgados con su propia logica de busqueda/seleccion.                                                                  |

`components/feedback/`:

| Componente  | Uso                                                     |
| ----------- | ------------------------------------------------------- |
| `Toast.tsx` | `useToast()` — `toast.success(...)`, `toast.error(...)` |

`components/layout/`:

| Componente             | Uso                                                                                                                                                                                                                                                                                           |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Screen.tsx`           | wrapper de pantalla: `SafeAreaView` + bg + padding + scroll/keyboard opcional                                                                                                                                                                                                                 |
| `NavBar.tsx`           | primitiva de barra superior: titulo, `canGoBack`, `NavIconButton`. No usar directo en pantallas autenticadas — ver `AppNavBar` abajo. `NavIconButton` siempre lleva `accessibilityRole="button"` y `accessibilityLabel` descriptivo (ej. "Volver", "Abrir menú").                             |
| `ListScreenHeader.tsx` | encabezado compartido de pantallas de listado: icono+kicker, titulo y boton primario opcional (`action`). Cada pantalla sigue armando su propia fila de metricas (`StatMetric`) y filtros (`FilterBar`) debajo. Usado por las 5 `*ListScreen.tsx` (clients/products/tenants/plans/documents). |

`features/navigation/` (no es `components/`, pero es transversal a todas las pantallas autenticadas):

| Archivo                                                                                 | Uso                                                                                                                                                                                                                |
| --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `components/AppNavBar.tsx`                                                              | envuelve `NavBar` y agrega menu hamburguesa (`NavigationMenu`) + menu de cuenta (`AccountMenu`/`UserAvatar`) segun `useAuthStore`. **Esta es la barra que usan las pantallas de `(app)/**`**, no `NavBar` directo. |
| `components/NavigationMenu.tsx`, `AccountMenu.tsx`, `MenuSurface.tsx`, `UserAvatar.tsx` | piezas internas de `AppNavBar`                                                                                                                                                                                     |
| `items.ts`                                                                              | items del menu de navegacion                                                                                                                                                                                       |

## Fechas Y Hora Ecuador

Toda fecha visible usa hora civil Ecuador (`America/Guayaquil`):

- Usar `lib/utils/ecuador-time.ts` para obtener fecha/hora actual Ecuador.
- Usar `formatDate` / `formatDateTime` de `lib/utils/format.ts` para renderizar fechas.
- No usar `toISOString().slice(0, 10)` para fechas de negocio: devuelve dia UTC y puede
  adelantar/atrasar la fecha local.
- No parsear `YYYY-MM-DD` con `new Date(value)` para mostrarlo; es una fecha civil, no un
  instante UTC.
- Epochs internos (`Date.now()` para idempotencia, JWT, toasts) pueden seguir como instantes
  tecnicos.

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

| Hook                                                           | Uso                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| -------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `useAsync`                                                     | ejecutar una promesa con estados loading/error                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| `useFetch<T>(fetcher)`                                         | fetch de un solo recurso: recibe `(() => Promise<T>) \| null` (null = no fetchear) y devuelve `{ data, loading, error, refresh }`. `fetcher` debe ser estable (`useCallback`) para evitar loops. Base de los hooks `use{Entity}` por dominio (`useClient`, `useTenant`, `usePlan`, `useAdminPlan`).                                                                                                                                                                                                                                                                                                                      |
| `useCursorPagedList<T, F>(filters, loadPage)`                  | listas con cursor opaco y controles de usuario: `items`, `page`, `pageSize`, `hasMore`, `totalItems`, `totalPages`, `canGoNext`, `canGoPrevious`, `refresh`, `nextPage`, `previousPage`, `setPageSize`. `totalItems`/`totalPages` vienen del campo `total` del backend (`null` si el endpoint no lo expone para ese filtro, ej. `q` activo en clients/products o `plan_status` en tenants — ver `BACKEND.md`). `filters` debe ser estable (estado/memo), no objeto inline. Sin `goToPage` (el cursor no permite saltar) — si el catalogo es acotado y se necesita salto de pagina, usar `useEagerPagedList` en su lugar. |
| `useEagerPagedList<T, F>(filters, loadPage, initialPageSize?)` | igual contrato que `useCursorPagedList` pero con `goToPage` real: camina secuencialmente TODAS las paginas del endpoint cursor-paginado existente (paginas de 50, tope de seguridad 20 paginas = 1000 items, expone `truncated` si se alcanza el tope) y pagina localmente con `useLocalPagedItems` sobre el set completo. No agrega backend nuevo. Usar solo en catalogos acotados por tenant donde cargar todo es razonable: `clients`, `products`, `tenants`. **No usar en `documents`** (crece sin limite en el tiempo).                                                                                             |
| `useLocalPagedItems<T>(items)`                                 | paginacion local para fuentes pequenas o endpoints que aun devuelven lista completa (ej. planes admin actual, o el set ya cargado por `useEagerPagedList`). Expone `totalItems`/`totalPages` reales (calculados de `items.length`) y `goToPage(n)` (clamp a `[1, totalPages]`) porque la lista completa ya esta en memoria.                                                                                                                                                                                                                                                                                              |
| `usePaginatedList<T, F>(filters, loadPage)`                    | legacy/infinite scroll. No usar en listados operativos nuevos; queda solo como compatibilidad hasta eliminarlo.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `useDebouncedSearch(value, onSearchChange, opts?)`             | logica de debounce detras de `SearchInput`: emite `onSearchChange(query)` solo cuando el texto consultable cambia (no en cada render del consumidor) y nunca emite una busqueda vacia fantasma al montar. Si necesitas un input de busqueda, usa `SearchInput`; usa este hook directo solo si necesitas la logica sin el `Input` visual.                                                                                                                                                                                                                                                                                 |
| `useRefreshOnFocus(refresh, opts?)`                            | refresca datos de listado/detalle cuando la ruta vuelve a foco (volver de crear/editar). `skipInitial` (default `true`) evita refrescar en el primer mount. Usar en toda pantalla con `useFetch`/`useCursorPagedList` para que crear/editar y volver muestre datos actualizados sin pull-to-refresh manual.                                                                                                                                                                                                                                                                                                              |
| `useFormSubmit<TArgs>(action)`                                 | analogo de escritura a `useFetch`: envuelve una accion async (crear/actualizar/cambiar estado/borrar) con `submitting`/`error` + el try/catch/finally + `toApiError` estandar. Devuelve `{ submitting, error, submit }`, donde `submit` es `(...args: TArgs) => Promise<void>` (asignable a props `onPress`/`onConfirm`/`onSubmit` con retorno `void`). Usar siempre que una pantalla haga un submit/accion con loading+error, en vez de repetir `useState` + try/catch.                                                                                                                                                 |
| `useCertificateFilePicker(init?)`                              | selector de archivo `.p12`/`.pfx` (web-only): devuelve `{ fileName, certificateB64, error, pickFile, reset }`. Usado por `RegisterCertificateScreen` (onboarding) y `CertificateSection` (gestion post-onboarding, ver `ONBOARDING.md`/`CERTIFICATES.md`).                                                                                                                                                                                                                                                                                                                                                               |

## Estado Global

La mayoria de features no necesitan estado global: datos de servidor se manejan con
`useFetch`/`useCursorPagedList`/`useAsync` por pantalla. Cuando si hace falta estado compartido entre
features (ej. sesion de auth en `features/auth/store.ts`), usar **Zustand** — ya es
dependencia del proyecto. No introducir Context API ni otra libreria de estado para esto.

## Reglas Generales

- Validar respuestas con Zod en `api.ts`.
- Mantener `types.ts` derivados de `schemas.ts` cuando aplique.
- Schema de validacion de formularios (`*FormValuesSchema` + tipo `*FormValues`) vive en
  `features/{area}/schemas.ts`, no inline en el componente `*Form.tsx`. El componente
  importa el schema y lo pasa a `zodResolver(...)`. Ver `clientFormValuesSchema`,
  `tenantFormValuesSchema`, `planFormValuesSchema`.
- No duplicar hooks de fetch/paginacion: `useFetch` para un solo recurso,
  `useCursorPagedList` para listas con cursor y `useLocalPagedItems` solo como transicion
  para listas locales pequenas.
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
4. Usar hooks existentes (`useAsync`, `useFetch`, `useCursorPagedList`) antes de crear uno nuevo.
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

### Render De Componentes: No Soportado Todavia

No existe ningun test que monte un componente real (`render()` de `@testing-library/react`
sobre un componente que importe `react-native`). Investigado:
`vitest`/Rolldown no puede parsear `node_modules/react-native/index.js` (sintaxis Flow).
Alias `react-native` → `react-native-web` (ya es dependencia, sin Flow) resuelve ese error
puntual, pero `react-native-web` necesita `@vitejs/plugin-react` (no instalado) para
JSX/runtime, y probablemente mas configuracion despues de eso — no confirmado cuanto mas
falta. Si se necesita testear render/interaccion de un componente, tratarlo como una tarea
de infra aparte (cambia `vitest.config.ts` para todo el repo), no como parte de la tarea que
lo pidio. Mientras tanto, lo testeable son funciones puras extraidas del componente
(`form.ts`, `filters.ts`, etc.) — patron ya usado en todo el repo.

## Deuda Tecnica

- `SelectField` nunca se construyo. `FormField`/`Input`/`SpecializedFields` cubrieron todos
  los campos migrados hasta ahora; crearlo cuando una pantalla necesite un selector real
  (lista cerrada de opciones, no segmented control de 2-4 valores).
- Tests de render de componentes bloqueados por infra — ver "Render De Componentes: No
  Soportado Todavia" arriba.
- Busqueda backend a escala: `q` in-memory no escala para miles/millones de filas. Resuelto
  solo para busqueda por identificador exacto/prefijo (`clients.identification` vía GSI
  `begins_with()`, ver `CLIENTS.md`); `products.sku`, `tenants.ruc` y el `q` general de
  `clients`/`products`/`documents` siguen sin indexacion dedicada — ver el `## Deuda
Tecnica` de cada dominio para el detalle especifico.
