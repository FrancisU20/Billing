# UX Refactor & Operability Roadmap

Estado: **En ejecucion por sprints**.

Ultima actualizacion: 2026-06-19.

## Lee Tambien Antes De Empezar

| Archivo                                   | Por que                                                     |
| ----------------------------------------- | ----------------------------------------------------------- |
| `CLAUDE.md`                               | Prioridad de producto, reglas no negociables, cierre con CI |
| `FRONTEND.md`                             | Design system, routing, componentes compartidos, hooks      |
| `BACKEND.md`                              | Paginacion opaca, DynamoDB, endpoints agregados             |
| `TENANTS.md`                              | Dashboard tenant/superadmin, permisos y datos de empresa    |
| `SUBSCRIPTIONS.md`                        | Billing, renovacion, `subscription_status`, pago fallido    |
| `INVOICES.md`                             | Listado de documentos, filtros SRI, metricas de facturacion |
| `CLIENTS.md` / `PRODUCTS.md` / `PLANS.md` | Listados, busquedas y formularios por dominio               |

## Objetivo

Convertir la app en una herramienta de facturacion operacional:

- Listados densos, paginados, refrescables y aptos para miles de registros.
- Busquedas reactivas con debounce y minimo de caracteres.
- Filtros minimalistas, consistentes y con calendario real.
- Formularios con validacion en vivo y componentes reutilizables.
- Acciones rapidas alineadas con backend: activar/inactivar, editar, eliminar/restaurar
  cuando el dominio lo soporte.
- Dashboard con contadores reales desde backend.
- Menos modulos visibles; configuraciones del tenant agrupadas en "Mi Perfil" / empresa.
- Componentes UI centralizados para evitar estilos y logica suelta por feature.

Alcance: **toda la app y todos los roles**. No limitar el refactor a dashboard tenant.
Aplica a pantallas tenant (`owner`, `admin`, `viewer`), superadmin, auth/onboarding,
marketing/legal cuando compartan componentes, y cualquier modulo futuro.

## Principios De Implementacion

- No arreglar pantalla por pantalla si el problema es transversal.
- Primero crear primitivas compartidas y despues migrar features.
- Mantener `tenant_id` desde JWT; nunca aceptar tenant desde filtros/body.
- Priorizar la mejor experiencia de usuario aunque implique mas trabajo backend.
- La paginacion por cursor opaco actual queda como compatibilidad interna/transicional.
  El objetivo de producto para listados operativos es paginacion real de cara al usuario:
  total de resultados, pagina actual, anterior/siguiente, selector 10/25/50 y salto a
  pagina cuando el volumen lo justifique.
- No implementar totales o salto arbitrario con scans completos. Si DynamoDB no lo da
  barato, crear soporte backend correcto: indices/GSIs, contadores materializados,
  tablas de busqueda, agregados por evento o un motor de busqueda dedicado segun el dominio.
- Busquedas remotas: ejecutar solo desde 3 caracteres, con debounce 350-500 ms,
  cancelacion/ignorancia de respuestas obsoletas y boton de limpiar.
- Fechas visibles y filtros de fecha usan hora civil Ecuador; no usar `new Date("YYYY-MM-DD")`
  para representar fechas civiles.
- Formularios: validacion en vivo por campo, mensajes cerca del input y bloqueo de submit
  si el schema local ya sabe que el payload es invalido.
- El frontend debe exponer de forma rapida y clara las capacidades reales del backend.
  Si un dominio tiene `active/inactive`, `status`, soft delete o transiciones de estado,
  la UI no puede obligar al usuario a entrar a editar para una accion comun.
- Crear/editar no debe sentirse como "cuadro tecnico": usar formularios guiados, secciones
  claras, ayudas por campo, validacion en vivo y acciones persistentes.
- Los descuentos son informacion comercial critica. Cualquier cambio de producto o campana
  global debe reflejarse inmediatamente en listados, selectores, facturador y totales
  visibles; si backend y frontend difieren, se trata como bug funcional.
- Todo componente compartido nuevo va en `components/ui/`, `components/layout/` o
  `lib/hooks/`; solo queda en `features/*/components` si es claramente especifico del dominio.
- Los sprints se implementan por vertical slices, pero cada patron aceptado debe migrarse
  a todos los modulos equivalentes: tenant y superadmin. No dejar una UX nueva en tenant
  y la UX vieja en superadmin para la misma clase de pantalla.

## Sprints

### Sprint 0 — Documentacion Y Auditoria UI

Objetivo: dejar inventario y reglas antes de tocar mas codigo.

Alcance:

- Crear este roadmap y enlazarlo desde `CLAUDE.md`.
- Actualizar `FRONTEND.md` con reglas nuevas de listados, filtros, busqueda, calendario
  y formularios.
- Auditar pantallas con patrones duplicados:
  - listados tenant: `documents`, `clients`, `products`
  - listados superadmin: `tenants`, `plans`
  - configuraciones tenant: establecimientos, descuento global, billing/suscripcion,
    certificado, perfil
  - filtros: `DocumentsFilters`, `ClientsFilters`, `ProductsFilters`, `PlansFilters`,
    `TenantsFilters`
  - formularios: `ClientForm`, `ProductForm`, `PlanForm`, `TenantForm`, onboarding,
    billing, emision de documentos
  - modales/pickers: `ClientPickerModal`, product picker, confirmaciones, menus
- Auditar alineacion backend/frontend por dominio:
  - campos `status`/`active`/`inactive` disponibles en backend sin accion rapida en UI
  - endpoints de cambio de estado que existen pero no estan expuestos
  - formularios que muestran campos tecnicos sin ayuda o sin validacion inmediata
- Auditar bugs de descuento:
  - campana global activa no se refleja claramente en pantalla de emision/totales
  - cambios de `discount_percentage` en productos no se reflejan despues de volver al listado
    o al selector
  - picker de productos/facturador puede estar usando datos stale si no refresca al foco
- Marcar deuda real, no deuda ya resuelta. La notificacion al comprador con XML/RIDE ya
  esta implementada y no debe figurar como pendiente.

Salida esperada:

- Roadmap versionado.
- Lista corta de componentes a crear/migrar.
- Lista de brechas backend/frontend por dominio y bugs de descuento priorizados.

### Sprint 1 — Freshness Y Paginacion Unificada

Objetivo: corregir que los listados no se refresquen al volver desde crear/editar/detalle
y reemplazar infinite scroll/cards por listas paginadas consistentes.

Backend:

- [x] Estandarizar `limit` permitido en endpoints listados: `10`, `25`, `50` (`DEFAULT_LIST_LIMIT`/
      `clamp_list_limit` ya existian; el frontend ya solo ofrece esas 3 opciones).
- [x] Agregar `total` al envelope de listado (`ApiResponse.paginated(..., total=...)`) en vez de
      rediseñar el contrato completo (`page`/`page_size`/`has_next`/`has_previous`): aditivo,
      no rompe `next_token`/`has_more` existentes. Ver `BACKEND.md` para el contrato exacto.
  - `clients`/`products`: `BaseRepository._count_raw()` — Query tenant-scoped + `Select=COUNT`,
    sin transferir items. `total=None` cuando `q`/`identification`/`sku` estan activos (se
    resuelven en Python, no en DynamoDB).
  - `documents`: `Select=COUNT` sobre el GSI `tenant-docs-index` (generalizacion de
    `count_this_month()`) cuando no hay `q`; cuando `q` esta activo, `count()` camina las
    paginas y cuenta coincidencias de `_matches_search()` igual que `list()` — sigue siendo
    exacto (a diferencia de clients/products/tenants, `total` nunca se omite aqui), solo
    mas costoso porque ya no puede usar `Select=COUNT`. `q` busca por serie, secuencial,
    comprador o clave de acceso (ver `INVOICES.md`); `serie` exacto sigue aceptado por
    compatibilidad pero el frontend ya solo envia `q`.
  - `tenants` (superadmin): Scan + `Select=COUNT`, igual costo que `list()` ya documentado
    como aceptable para catalogo B2B chico. `total=None` cuando `q`/`ruc`/`plan_status` estan
    activos (`plan_status` se computa en memoria, nunca se persiste).
  - `plans`: no requirio cambios — ya devuelve la lista completa y el frontend pagina local.
- [ ] Salto a pagina arbitraria (no solo Anterior/Siguiente): no implementado. Un cursor opaco
      de DynamoDB no soporta acceso aleatorio por numero de pagina sin indexacion adicional
      (offset materializado o GSI numerico); fuera de alcance hasta que el volumen lo justifique.

Frontend:

- [x] Crear `useRefreshOnFocus(refresh)` para refrescar cuando una ruta vuelve a foco.
- [x] Invalidar/refrescar datos despues de mutaciones y al volver a foco:
  - listados
  - detail screens
  - pickers/modales con busqueda
  - pantalla de emision de documentos
  - campana de descuento global
- [x] Reemplazar infinite scroll en listados operativos por modelo de pagina sobre
      cursor opaco mientras backend v2 queda pendiente:
  - `pageItems`
  - `pageIndex`
  - `pageSize`
  - `totalItems` / `totalPages` solo cuando el backend o la fuente local los expone
  - `canGoNext`
  - `canGoPrevious`
  - `nextPage()`
  - `previousPage()`
  - `refreshPage()`
- [x] Crear controles compartidos de paginacion (`ListPaginationControls`):
  - header compacto con titulo, accion primaria y contador local
  - selector de limite `10/25/50`
  - controles Anterior/Siguiente
  - indicador "Pagina X" con cursor, "Pagina X de Y" solo donde hay total real/local
  - empty/error/loading estandar
  - layout responsive: filas densas en web/tablet, filas compactas en movil
- [x] Migrar primero `DocumentsListScreen`, `ClientsListScreen`, `ProductsListScreen`,
      y despues los modulos superadmin `PlansListScreen` y `TenantsListScreen` con controles
      compartidos. `PlansListScreen` usa paginacion local porque su endpoint aun devuelve lista
      completa.

Criterio de aceptacion:

- [x] Crear/editar/eliminar y volver al listado muestra datos actualizados sin pull-to-refresh manual.
- [x] Cambiar descuento de producto o campana global se refleja al volver al listado, selector
      y facturador.
- [x] Los listados migrados ya no dependen de `onEndReached` para carga principal.
- [x] El usuario puede elegir 10/25/50 por pagina y ver el total de resultados/paginas
      (`ListPaginationControls` muestra "Pagina X de Y" + "N resultados en total" cuando el
      backend expone `total`; cae a "Pagina X" + "N registros en esta pagina" cuando hay un
      filtro de texto libre activo, ya que ese total no es exacto). Ir a una pagina arbitraria
      (no solo Anterior/Siguiente) queda pendiente — ver nota de backend arriba.

### Sprint 1.5 — Alineacion Backend/Frontend De Acciones De Estado

Objetivo: exponer en UI las transiciones de estado que ya existen en backend, sin obligar
al usuario a abrir formularios completos.

Alcance:

- Auditar dominios con `status`, `active/inactive` o soft delete:
  - [x] clientes — solo tenia "Eliminar" (= `status=inactive`); faltaba reactivar
  - [x] productos — mismo gap que clientes
  - [x] planes — ya tenia `setStatus` + `ConfirmDialog` (Sprint previo a este roadmap)
  - [x] tenants — ya tenia `changeStatus` con confirmaciones en `TenantDetailScreen`
  - [x] campanas/descuentos — auditado: `DiscountCampaignScreen` y
        `EstablishmentsScreen`/`EstablishmentCard` mostraban controles de edicion a
        cualquier rol (incluyendo `viewer`), pese a que el backend ya exigia
        `owner|admin` (`PUT /products/discount-campaign`, mutaciones de
        `lambdas/sequences/handler.py`). Corregido: `DiscountCampaignScreen` muestra
        `DetailSection` de solo lectura para `viewer` en vez del formulario;
        `EstablishmentsScreen`/`EstablishmentCard` ocultan "Nuevo establecimiento",
        "Punto de emisión" y "Editar punto" cuando `!canWrite(role)`.
  - [x] documentos — confirmado que no aplica accion de estado (solo lectura del
        resultado SRI); no requiere cambios.
- Crear acciones rapidas reutilizables (clientes y productos, via PATCH existente con
  `status` parcial — no hizo falta endpoint nuevo):
  - [x] accion "Activar" en `ClientListItem`/`ProductListItem` cuando el item esta
        inactivo (reemplaza "Eliminar" en ese estado; activo conserva "Eliminar" como
        unico camino a inactivo, sin duplicar botones)
  - [x] menu de acciones por fila: `components/ui/RowActionsMenu.tsx` (action sheet
        generico, reemplaza 2-3 `ListItemAction` planos por un solo boton "⋮" + hoja de
        acciones). Migrado a `ClientListItem`, `ProductListItem`, `PlanListItem` — los
        3 listados con 2+ acciones mutables por fila. `TenantListItem`/`DocumentListItem`
        no se tocaron: tienen como maximo 1 accion mutable (o ninguna), un menu ahi seria
        un paso extra sin beneficio.
  - [x] confirmacion para activar (`ConfirmDialog`, mismo patron que plans/tenants)
  - [x] feedback inmediato + refresh del listado (`useFormSubmit` + `refresh()`)
- Agregar permisos visibles (clientes y productos):
  - [x] ocultar Editar/Eliminar/Activar y el boton "Nuevo X" cuando el rol es `viewer`
        (`canWrite(role)` de `constants/roles.ts`, ya existia pero no estaba conectado aqui)
  - [x] mostrar solo lectura para `viewer` (`canManage` gating en ambos list screens)
  - [x] mantener validacion backend como fuente final (sin cambios — el PATCH ya
        exigia `owner|admin`)

Criterio de aceptacion:

- [x] Si backend soporta `active/inactive`, la UI permite cambiarlo desde listado
      con confirmacion cuando corresponda (clientes, productos, planes, tenants).
- [x] El cambio de estado se refleja sin recargar manualmente.
- [x] No hay acciones visibles que el rol actual no pueda ejecutar (clientes, productos,
      campana de descuento, establecimientos/puntos de emision).

### Sprint 2 — Busqueda Y Filtros Minimalistas

Objetivo: hacer busquedas y filtros usables sin saturar DynamoDB ni la UI.

Frontend:

- [x] Crear `SearchInput` compartido:
  - icono de busqueda
  - boton limpiar
  - debounce configurable
  - minimo 3 caracteres para busqueda remota
  - busqueda vacia limpia filtro
  - estado "Escribe al menos 3 caracteres" sin llamar backend
- [x] Migrar busquedas principales a `SearchInput`:
  - `ProductsListScreen`
  - `ClientsFilters`
  - `TenantsFilters`
  - `PlansFilters`
  - `DocumentsFilters` (busqueda general `q`: serie, secuencial, comprador o clave de
    acceso — reemplazo de la busqueda exacta por `serie` que tenia al migrar este sprint)
  - `ProductPickerModal`
  - `ClientPickerModal`
- [x] Crear `FilterBar` compartido (`components/ui/FilterBar.tsx`):
  - filtros principales siempre visibles (children)
  - filtros secundarios colapsados detras de "Mas filtros" con badge de cantidad activa
    (panel inline expandible, no bottom sheet/modal separado por plataforma — suficiente
    para la densidad de filtros actual; revisar si el numero de filtros secundarios crece)
  - chips de filtros activos con opcion de borrar individualmente (`x` en el chip ->
    limpia ese campo del draft y aplica de inmediato, sin esperar al boton "Aplicar")
  - boton "Limpiar" siempre visible
- [x] Migrar filtros por dominio a `FilterBar`: `ClientsFilters`, `TenantsFilters`,
      `PlansFilters`, `DocumentsFilters`. `ProductsListScreen` no se migro: solo tiene un
      filtro secundario (`kind`), no amerita panel colapsable todavia.
  - Helpers de chips puros y testeados por dominio en cada `features/*/filters.ts`:
    `clientFilterChips`/`clearClientFilterField`, `tenantFilterChips`/`clearTenantFilterField`,
    `planFilterChips`/`clearPlanFilterField`, `documentFilterChips`/`clearDocumentFilterField`.
  - `FilterBlock`/`FilterPill` extraidos a `components/ui/FilterBlock.tsx` (antes duplicados
    en cada `*Filters.tsx`).

Backend:

- Revisar `q` por dominio:
  - `clients` y `products` pueden seguir con v1 in-memory por ahora, pero documentar el
    limite operativo.
  - `documents` agrego `q` (serie/secuencial/comprador/clave de acceso) sobre el GSI
    `tenant-docs-index` con el mismo patron in-memory (`_matches_search()`); mismo limite
    operativo que clients/products, documentado en `INVOICES.md`.
  - Si un dominio requiere busqueda real a escala, planificar GSI/Search index especifico,
    no scans masivos.

Criterio de aceptacion:

- [x] Escribir 1-2 caracteres no llama al backend en busquedas migradas.
- [x] Al tercer caracter la busqueda filtra automaticamente en listados/pickers migrados.
- [x] Filtros activos son visibles como chips y faciles de limpiar (clients/tenants/plans/documents).

### Sprint 3 — Calendario Y Fechas

Estado: **implementado para filtros de listados**.

Objetivo: eliminar inputs manuales de fecha con formato fragil.

Frontend:

- [x] Crear `DateRangePicker` compartido:
  - modal propio compatible RN/Web, sin dependencia externa
  - calendario mensual con navegacion anterior/siguiente
  - presets: Hoy, Esta semana, Este mes, Limpiar
  - salida canonica `YYYY-MM-DD` civil Ecuador
  - rango ordenado automaticamente (`desde <= hasta`)
- [x] Reemplazar filtros `created_from/to`, `date_from/to`, `issued_from/to` en listados:
  - `DocumentsFilters` (`date_from`/`date_to`, fecha de emision)
  - `ClientsFilters` (`created_from`/`created_to`)
  - `TenantsFilters` (`created_from`/`created_to`)
  - `PlansFilters` (`created_from`/`created_to`)
- [x] Agregar helpers testeados en `lib/utils/date-range.ts` para fechas civiles sin
      `new Date("YYYY-MM-DD")` ni `toISOString().slice(...)`.

Backend:

- [x] Mantener contratos existentes y parsing backend sin cambios.
- [x] No se detecto parsing inconsistente que requiera tests backend nuevos en este sprint.

Criterio de aceptacion:

- [x] Ningun filtro de listado migrado pide escribir fechas manualmente.
- [x] Rango invalido se corrige antes de llegar al backend.

### Sprint 4 — Formularios Y Validacion En Vivo

Estado: **en ejecucion**.

Objetivo: formularios mas claros, amigables, con validacion inmediata y componentes
centralizados.

Frontend:

- Crear/fortalecer componentes:
  - [x] `FormField`
  - [x] `Input`
  - [ ] `SelectField`
  - [x] `MoneyField` (`SpecializedFields.tsx`)
  - [x] `PercentField` (`SpecializedFields.tsx`)
  - [x] `EmailField` (`SpecializedFields.tsx`)
  - [x] `RucField` (`SpecializedFields.tsx`)
  - [x] `IdentificationField` (`SpecializedFields.tsx`)
  - [x] `PhoneField` (`SpecializedFields.tsx`)
  - [x] `FormActions`
- Crear `validators`/helpers compartidos para:
  - [x] email (Zod schemas)
  - [x] RUC (`lib/utils/ruc.ts` + schemas tenant/client)
  - [x] cedula (`lib/utils/ruc.ts` + schema client)
  - [x] dinero decimal (`lib/utils/form-validators.ts`)
  - [x] porcentaje (`lib/utils/form-validators.ts`)
  - [x] secuencial/serie SRI — ya existia, solo estaba sin marcar: `code` de
        establecimiento/punto de emision valida `^\d{3}$` (`features/sequences/schemas.ts`,
        `createEstablishmentSchema`/`addEmissionPointSchema`) y `initial_sequential` valida
        entero 1-999999999, ambos con test en `schemas.test.ts`. No se centralizo en
        `lib/utils/form-validators.ts` porque es de un solo dominio (`sequences`); seguiria
        la regla de FRONTEND.md de no compartir algo que solo usa 1 feature.
- Configurar formularios para `mode: "onChange"` o equivalente, con mensajes por campo:
  - [x] `ClientForm`
  - [x] `TenantForm`
  - [x] `PlanForm`
  - [x] `RegistrationForm` (onboarding)
  - [x] `ProductForm` ya estaba en vivo; se conecto a campos especializados.
  - [x] `EmitDocumentScreen` ya estaba en vivo.
  - [x] `PayerForm` valida email y cedula/RUC antes de habilitar pago.
  - [x] Acciones de submit centralizadas con `FormActions` en `ClientForm`, `ProductForm`,
        `TenantForm`, `PlanForm` y `RegistrationForm`.
- Revisar formularios sin schema o con validacion tardia.
- Redisenar pantallas de crear/editar como experiencias guiadas:
  - secciones cortas con titulos de negocio
  - ayuda contextual debajo de campos complejos
  - acciones visibles y consistentes
  - evitar formularios largos sin agrupacion
  - preservar datos si ocurre error de API
- Prioridad de migracion:
  - emitir documento
  - productos
  - clientes
  - tenants
  - planes
  - billing/onboarding
  - superadmin tenants/plans

Backend:

- No relajar validaciones server-side. La validacion frontend mejora UX; backend sigue
  siendo fuente de seguridad.

Criterio de aceptacion:

- [x] Email invalido muestra error antes del submit en formularios migrados.
- [x] Campos fiscales invalidos muestran mensaje local claro en clientes/tenants.
- [x] Submit se deshabilita si el formulario local esta invalido en clientes/tenants/plans/products/documents/onboarding; billing bloquea el pago hasta tener pagador valido.
- Crear/editar se entiende sin conocer detalles tecnicos del backend.

### Sprint 4.5 — Descuentos En UI Y Consistencia Comercial

Objetivo: corregir la inconsistencia visual/funcional de descuentos entre productos,
campana global y facturador.

Hipotesis iniciales a validar:

- Producto actualizado con `discount_percentage` no se refleja por falta de refresh al
  volver al listado o al picker.
- Campana global activa se usa como techo/sugerencia, pero la pantalla de emision no
  comunica ni recalcula suficientemente cuando cambia la campana o la linea.
- El usuario espera ver el descuento aplicado/sugerido en pantalla antes de emitir, no
  solo que backend lo valide.

Alcance:

- Definir comportamiento de producto:
  - [x] si el producto tiene descuento, mostrarlo en detalle y picker
  - [x] si el producto tiene descuento, mostrarlo en listado (`ProductListItem`) y picker
  - [x] linea de factura: descuento sugerido visible y aplicado en `EmitDocumentScreen`,
        con fuente (`Catalogo`/`Campana`) y monto sugerido por linea
  - [x] si se edita el descuento, invalidar/refrescar listados y pickers (via
        `useRefreshOnFocus` de Sprint 1)
- Definir comportamiento de campana global:
  - [x] mostrar campana activa en facturador de forma visible pero no invasiva (banner sobre
        lineas de detalle + resumen de descuento sugerido)
  - [x] al seleccionar producto, mostrar porcentaje sugerido y aplicarlo automaticamente
        (`resolveSuggestedDiscount` + `shouldAutoApplySuggestedDiscount`)
  - [x] para lineas manuales, recalcular el techo sugerido cuando cambia la campana o la
        linea (mismo auto-apply corre para lineas sin `product_id`, usando el techo de
        campana)
  - [x] recalcular totales visibles inmediatamente
- Tests:
  - [x] tests frontend para `resolveSuggestedDiscount`, `resolveDiscountPolicy` y
        `shouldAutoApplySuggestedDiscount`
        (`form.test.ts`)
  - [ ] **tests de render/cambio de lineas a nivel componente (`EmitDocumentScreen`) —
        bloqueado por infraestructura, no por falta de tiempo.** El proyecto no tiene
        testing de componentes en ningun lado (solo hooks/funciones puras): `vitest` no
        puede ni parsear `react-native` directamente (sintaxis Flow en
        `node_modules/react-native/index.js`). Investigado: alias a `react-native-web`
        (ya es dependencia, sin Flow) resuelve ESE error puntual, pero `react-native-web`
        necesita `@vitejs/plugin-react` (no instalado) para JSX/runtime, y probablemente
        mas configuracion despues de eso — no se llego a confirmar cuanto mas falta.
        Es trabajo de infra transversal (afecta `vitest.config.ts` para todo el repo, no
        solo este test), no una tarea chica — requiere su propia sesion dedicada si se
        decide priorizar. No se dejo nada a medias: `vitest.config.ts` quedo intacto.
- [ ] Agregar tests backend si se detecta diferencia entre preview frontend y validacion de
      `EmitDocumentUseCase` (sin diferencia detectada hasta ahora; backend no tuvo cambios
      en este sprint)

Criterio de aceptacion:

- [x] Cambiar descuento de producto se ve en productos, picker y facturador sin refresh manual.
- [x] Activar/cambiar campana global se ve en facturador y totales visibles.
- [x] El descuento que el usuario ve antes de emitir coincide con lo que backend acepta y persiste.

### Sprint 5 — Dashboard Operacional

Estado: **completo para el alcance de este roadmap** (conteos, limite del plan y "todo
bien" de suscripcion via Sprint 6).

Objetivo: reemplazar contadores placeholder por metricas reales.

**Dashboard superadmin: fuera de alcance de `UX_REFACTOR.md`.** Es un sprint de producto
aparte (metricas globales: tenants por estado/plan, ingresos estimados — ver `TENANTS.md`
seccion "Dashboard Superadmin — Pendiente"), no una migracion de UX de algo que ya existe.
No se planifica aqui; se retomo cuando ese sprint se priorice explicitamente.

Backend:

- [x] Crear endpoint agregado tenant en dominio `documents`: `GET /documents/summary`
      (`GetDocumentsSummaryUseCase` + `DynamoDocumentsRepository.summary_this_month()`,
      `DocumentSummary.to_dict()` en `backend/lambdas/documents/domain/entities.py`).
  - [x] documentos emitidos del periodo (`issued_count`)
  - [x] autorizados/rechazados/fallidos (`authorized_count`/`rejected_count`/`failed_count`,
        mas `pending_count`/`processing_count` para "en proceso")
  - [x] total autorizado del periodo (`authorized_total`)
  - [x] **consumo del limite mensual del plan.** `_summary` resuelve el tenant + su plan
        igual que `_emit` (`_get_tenant`/`_get_plan`, mismo `DynamoPlanReader` ya usado por
        `EmitDocumentUseCase`) y selecciona `pruebas_monthly_docs_limit` o `document_limit`
        segun `tenant.sri_environment` — el mismo numero que aplica la verificacion real al
        emitir. `GetDocumentsSummaryUseCase.execute(tenant_id, monthly_limit)` adjunta
        `document_limit`/`is_unlimited` (`-1` = ilimitado) al `DocumentSummary` inmutable via
        `dataclasses.replace`; el repositorio de documents sigue sin saber nada de planes.
        Si el plan no se puede resolver (`ValidationError` — ej. plan desactivado por
        superadmin con tenants aun suscritos), `_resolve_monthly_limit` lo atrapa y devuelve
        `None`: el summary completo no se cae, solo se omite el limite (`document_limit:
        null`). No se toco el comportamiento de `_emit` (sigue sin ese guard).
  - [ ] estado certificado y dias para expirar — **no via este endpoint**, pero ya visible
        en el dashboard: `TenantDashboardScreen` renderiza `CertificateSection` (componente
        preexistente de `TENANTS.md`/`CERTIFICATES.md`) debajo del resumen, con el mismo
        badge de dias-para-expirar que usa el resto de la app. No hace falta duplicarlo en
        el payload de `/documents/summary`.
  - [x] estado suscripcion — **no via este endpoint, resuelto en Sprint 6**.
        `PendingActivationBanner`/`PaymentFailedBanner` ya cubren los estados con problema
        a nivel de layout tenant; el widget informativo de "todo bien" se agrego en
        `BillingScreen` (card "Tu suscripción está al día" cuando `subscription_status ===
        'active'`, ver Sprint 6) en vez de en el dashboard — es donde el usuario ya espera
        mirar el estado de su plan, y evita sumar otra card mas al dashboard.
- [x] Evitar scans caros no acotados en el primer corte: summary usa Query por
      `tenant-docs-index` acotado al mes civil Ecuador y suma solo ese rango.
      Si se requieren historicos largos, crear tabla/materializacion por evento o worker.

Frontend:

- [x] Reemplazar placeholders del dashboard tenant por datos reales (`TenantDashboardScreen`
      via `useDocumentsSummary`):
  - emitidos del mes
  - autorizados
  - rechazados/fallidos
  - total autorizado
  - progreso de autorizacion del mes
  - [x] consumo del limite mensual del plan: card "Limite del plan" con barra de progreso
        (verde <80%, ambar 80-99%, rojo >=100%) cuando `document_limit` esta presente;
        badge "Ilimitado" cuando `is_unlimited`; no se muestra nada cuando el backend no
        pudo resolver el plan (`document_limit: null`) — degradacion silenciosa, no error.
- [x] Agregar loading/error por bloque, no pantalla entera si solo falla una metrica
      (`ApiErrorBanner` del resumen sin bloquear tenant/certificado).

Criterio de aceptacion:

- [x] Dashboard tenant muestra numeros reales despues de emitir documentos.
- [x] Dashboard tenant no usa contadores `—`; cae a `0` si aun no hay actividad.
- [x] El usuario ve cuanto le queda de su limite mensual del plan antes de toparse con
      `DocumentLimitReachedError` al emitir (card "Limite del plan" en el dashboard).

### Sprint 6 — Reorganizacion De Modulos Y Perfil/Empresa

Estado: **implementado**.

Objetivo: reducir ruido en navegacion y agrupar configuraciones relacionadas.

Frontend:

- [x] Crear pantalla "Empresa" (`CompanyScreen`, ruta `/(app)/(tenant)/settings/company`):
  - [x] Datos de empresa — resumen de solo lectura (`DetailSection`/`DetailField`, mismas
        primitivas que `TenantDetailScreen`) + boton "Editar datos" solo si `canWrite(role)`.
  - [x] Certificado digital — reusa `CertificateSection` (mismo componente que ya usaban
        `TenantDashboardScreen` y `TenantDetailScreen`; no se duplico logica).
  - [x] Establecimientos y puntos de emision — fila de navegacion a la pantalla existente
        (`EstablishmentsScreen`, sin cambios).
  - [x] Descuento global — fila de navegacion a `DiscountCampaignScreen` (sin cambios).
  - [x] Suscripcion y facturacion — fila de navegacion a `BillingScreen` (con el ajuste de
        pago manual, ver Suscripciones abajo).
  - No se hizo como tabs dentro de una sola pantalla: es un hub con secciones inline
    (datos + certificado) y filas de navegacion hacia las pantallas existentes — evita
    reescribir `EstablishmentsScreen`/`DiscountCampaignScreen`/`BillingScreen`, que ya son
    pantallas completas con su propio CRUD/estado.
  - "Usuario/perfil" no se tocó: sigue siendo `ProfileScreen` (`/(app)/profile`, ya
    existía antes de este roadmap) — es una pantalla separada, no una tab de "Empresa",
    porque aplica tambien a superadmin (que no tiene "empresa").
  - [x] `CompanyEditScreen` (`/settings/company/edit`) — nueva pantalla de self-edit del
        tenant, reusa `TenantForm` en `mode="edit"` (RUC ya queda deshabilitado por el
        propio form en ese modo; no hay seccion de Plan en `mode="edit"`, consistente con
        que `UpdateTenantCommand` no acepta `plan_id`). Redirige con `<Redirect>` si el rol
        no tiene permiso de escritura, aunque ademas el backend ya exigia `owner|admin` en
        `PATCH /tenants/{id}` (defensa en profundidad, no el unico guard).
- [x] Ocultar modulos secundarios del menu principal: `items.ts` ya no lista
      "Establecimientos"/"Descuento global"/"Facturación" — se reemplazaron por un unico
      item "Mi empresa" que abre el hub.
- [x] Aplicar permisos:
  - viewer: `CompanyScreen` no muestra el boton "Editar datos"; `CertificateSection` ya
    recibe `canManage` propio.
  - admin/owner: pueden editar datos de empresa y certificado.
  - superadmin: no aplica — el hub es tenant-only (superadmin tiene su propia navegacion
    sin "Mi empresa").
- [x] Paridad UX tenant/superadmin donde el caso de uso es equivalente: `CompanyScreen`
      reusa exactamente `DetailSection`/`DetailField`/`CertificateSection`, las mismas
      primitivas que ya usaba `TenantDetailScreen` (vista superadmin de un tenant) — no se
      crearon primitivas nuevas y paralelas.

Suscripciones:

- [x] Ajustar UI de pago manual (`BillingScreen`):
  - [x] no permitir pago anticipado si el plan esta vigente: el card de "Renovar
        suscripción"/"Pagar con tarjeta nueva" solo se muestra cuando
        `subscription_status !== 'active'`.
  - [x] cuando esta `active`, se muestra un card informativo ("Tu suscripción está al día")
        en vez del boton de pago — refuerza que el cobro automatico es el camino principal.
  - [x] el boton sigue habilitado para `expired`/`payment_failed` (motivo de pago manual
        real); no se introdujo una regla de "ultimos N dias" porque `SUBSCRIPTIONS.md` no
        define ese grace period — si se necesita, es una decision de negocio nueva, no un
        ajuste de UI.
  - [x] cobro automatico via `dlocal_payer_id` (ver `SUBSCRIPTIONS.md`) sigue siendo el
        camino principal sin cambios; esto solo oculta el camino manual cuando no aplica.

Criterio de aceptacion:

- [x] Menu principal queda enfocado en operacion diaria (Dashboard, Clientes, Productos,
      Documentos, Mi empresa).
- [x] Configuraciones de empresa no aparecen como modulos sueltos — viven bajo "Mi empresa".
- [x] Billing no invita a pagar antes de tiempo.

### Sprint 7 — Centralizacion Final De Componentes

Objetivo: cerrar deuda de duplicacion UI.

Alcance:

- Extraer a compartidos cualquier patron usado por 2+ features:
  - pickers con busqueda
  - modales de seleccion
  - barras de acciones
  - estados vacios
  - filtros
  - tablas/listas
  - inputs especializados
- Eliminar estilos duplicados de pantallas que ya puedan usar primitivas.
- Actualizar `features/design-system/screens/ComponentsScreen.tsx` con los componentes nuevos.
- Actualizar `FRONTEND.md` con la lista final.

Criterio de aceptacion:

- Nuevas pantallas pueden armarse con componentes compartidos sin copiar estilos.
- `ClientPickerModal` deja de figurar como deuda si se generaliza.

## Orden Recomendado De Ejecucion

1. Sprint 1: freshness + paginacion. Es el bug operativo mas visible.
2. Sprint 2: busqueda/filtros. Depende de la base de listados.
3. Sprint 3: calendario. Se integra naturalmente con filtros.
4. Sprint 4: formularios. Reduce errores de datos.
5. Sprint 1.5: acciones rapidas de estado. Debe ir cerca de listados porque comparte filas/acciones.
6. Sprint 4.5: descuentos UI. Prioridad alta por impacto comercial directo en facturacion.
7. Sprint 5: dashboard. Requiere backend agregado y debe ir despues de estabilizar UX base.
8. Sprint 6: reorganizacion de modulos. Conviene cuando componentes/listados ya estan estables.
9. Sprint 7: limpieza final y design-system.

## Riesgos Y Decisiones Pendientes

- Paginacion con total exacto y salto a pagina: es requisito de UX para listados
  operativos. Requiere agregado/counter/indexacion por dominio; no hacerlo con scan
  completo.
- Busqueda a gran escala: `q` in-memory no escala para miles/millones. Aceptable como
  primer paso con minimo 3 caracteres y limites bajos; para alto volumen se requiere GSI
  o buscador dedicado.
- Calendario: elegir dependencia compatible con Expo v56 o implementar wrapper propio
  sobre componentes nativos/web. No instalar librerias sin validar mantenimiento y bundle.
- Dashboard: si las metricas son costosas, materializar por eventos en vez de calcular
  todo al vuelo.
- Descuentos: hay que decidir explicitamente si la campana global solo sugiere/limita o
  si debe autoaplicarse a todas las lineas. La UI debe reflejar esa decision sin ambiguedad.
