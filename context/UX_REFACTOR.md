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
  - `documents`: mismo patron de `Select=COUNT` sobre el GSI `tenant-docs-index`
    (generalizacion de `count_this_month()`). Siempre exacto: ningun filtro de documents es
    de texto libre.
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
  - [ ] campanas/descuentos — no auditado todavia
  - [ ] documentos — no aplica accion de estado (solo lectura del resultado SRI)
- Crear acciones rapidas reutilizables (clientes y productos, via PATCH existente con
  `status` parcial — no hizo falta endpoint nuevo):
  - [x] accion "Activar" en `ClientListItem`/`ProductListItem` cuando el item esta
        inactivo (reemplaza "Eliminar" en ese estado; activo conserva "Eliminar" como
        unico camino a inactivo, sin duplicar botones)
  - [ ] menu de acciones por fila (hoy son botones planos en `ListItemAction`, no menu)
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
- [x] No hay acciones visibles que el rol actual no pueda ejecutar (clientes, productos).

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
  - `DocumentsFilters` para serie
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
  - Si un dominio requiere busqueda real a escala, planificar GSI/Search index especifico,
    no scans masivos.

Criterio de aceptacion:

- [x] Escribir 1-2 caracteres no llama al backend en busquedas migradas.
- [x] Al tercer caracter la busqueda filtra automaticamente en listados/pickers migrados.
- [x] Filtros activos son visibles como chips y faciles de limpiar (clients/tenants/plans/documents).

### Sprint 3 — Calendario Y Fechas

Objetivo: eliminar inputs manuales de fecha con formato fragil.

Frontend:

- Crear `DateRangePicker` compartido:
  - web: calendario/popover accesible
  - movil: selector nativo o modal propio segun compatibilidad Expo
  - presets: Hoy, Esta semana, Este mes, Limpiar
  - salida canonica `YYYY-MM-DD` civil Ecuador
- Reemplazar filtros `created_from/to`, `date_from/to`, `issued_from/to`.
- Validar rango: desde <= hasta.

Backend:

- Mantener `parse_date_boundary` y conversion a limites UTC en backend.
- Agregar tests si algun endpoint tiene parsing inconsistente.

Criterio de aceptacion:

- Ningun listado pide escribir fechas manualmente.
- Rango invalido se comunica antes de llamar al backend.

### Sprint 4 — Formularios Y Validacion En Vivo

Objetivo: formularios mas claros, amigables, con validacion inmediata y componentes
centralizados.

Frontend:

- Crear/fortalecer componentes:
  - `FormField`
  - `Input`
  - `SelectField`
  - `MoneyInput`
  - `PercentInput`
  - `EmailInput`
  - `RucInput`
  - `IdentificationInput`
  - `PhoneInput` si aplica
  - `FormActions`
- Crear `validators`/helpers compartidos para:
  - email
  - RUC
  - cedula
  - dinero decimal
  - porcentaje
  - secuencial/serie SRI
- Configurar formularios para `mode: "onChange"` o equivalente, con mensajes por campo.
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

- Email invalido muestra error antes del submit.
- Campos fiscales invalidos muestran mensaje local claro.
- Submit se deshabilita si el formulario local esta invalido.
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
  - [ ] si el producto tiene descuento, mostrarlo en listado (`ProductsListScreen` aun sin
        columna/indicador de descuento)
  - [x] linea de factura: descuento sugerido visible y aplicado en `EmitDocumentScreen`
  - [x] si se edita el descuento, invalidar/refrescar listados y pickers (via
        `useRefreshOnFocus` de Sprint 1)
- Definir comportamiento de campana global:
  - [x] mostrar campana activa en facturador de forma visible pero no invasiva (hint sobre
        lineas de detalle)
  - [x] al seleccionar producto, mostrar porcentaje sugerido y aplicarlo automaticamente
        (`resolveSuggestedDiscount` + `shouldAutoApplySuggestedDiscount`)
  - [x] para lineas manuales, recalcular el techo sugerido cuando cambia la campana o la
        linea (mismo auto-apply corre para lineas sin `product_id`, usando el techo de
        campana)
  - [x] recalcular totales visibles inmediatamente
- Tests:
  - [x] tests frontend para `resolveSuggestedDiscount` y `shouldAutoApplySuggestedDiscount`
        (`form.test.ts`)
  - [ ] tests de render/cambio de lineas a nivel componente (`EmitDocumentScreen`) — no
        existen todavia, solo tests de las funciones puras
- [ ] Agregar tests backend si se detecta diferencia entre preview frontend y validacion de
      `EmitDocumentUseCase` (sin diferencia detectada hasta ahora; backend no tuvo cambios
      en este sprint)

Criterio de aceptacion:

- Cambiar descuento de producto se ve en productos, picker y facturador sin refresh manual.
- Activar/cambiar campana global se ve en facturador y totales visibles.
- El descuento que el usuario ve antes de emitir coincide con lo que backend acepta y persiste.

### Sprint 5 — Dashboard Operacional

Objetivo: reemplazar contadores placeholder por metricas reales.

Backend:

- Crear endpoint agregado tenant, por ejemplo `GET /dashboard/summary`:
  - documentos emitidos del periodo
  - autorizados/rechazados/fallidos
  - total facturado del periodo
  - consumo del limite mensual del plan
  - estado certificado y dias para expirar
  - estado suscripcion
- Evaluar endpoint superadmin separado si se necesita metricas globales.
- Evitar scans caros no acotados; si el agregado no es barato, crear tabla/materializacion
  por evento o worker.

Frontend:

- Reemplazar placeholders del dashboard por datos reales.
- Definir tambien dashboard/resumen superadmin si el modulo superadmin necesita metrica
  operativa global.
- Agregar loading/error por bloque, no pantalla entera si solo falla una metrica.

Criterio de aceptacion:

- Dashboard muestra numeros reales despues de emitir documentos.
- Superadmin no queda con placeholders si tiene resumen operativo.
- No hay contadores `—` salvo falta real de datos.

### Sprint 6 — Reorganizacion De Modulos Y Perfil/Empresa

Objetivo: reducir ruido en navegacion y agrupar configuraciones relacionadas.

Frontend:

- Crear pantalla "Mi Perfil" / "Empresa" con tabs o secciones:
  - Usuario/perfil
  - Datos de empresa
  - Certificado digital
  - Establecimientos y puntos de emision
  - Descuento global
  - Suscripcion y facturacion
- Ocultar modulos secundarios del menu principal cuando vivan bajo perfil/empresa.
- Aplicar permisos:
  - viewer: lectura donde corresponda
  - admin/owner: configuraciones tenant
  - superadmin: gestion global
- Mantener paridad UX entre vistas tenant y superadmin: mismas primitivas de listado,
  filtros, formularios, modales y acciones cuando el caso de uso sea equivalente.

Suscripciones:

- Ajustar UI de pago manual:
  - no permitir pago anticipado si el plan esta vigente
  - habilitar boton solo cuando el estado/ciclo lo requiera (`expired`, `payment_failed`,
    o la regla de negocio que se defina en `SUBSCRIPTIONS.md`)
  - mantener cobro automatico como camino principal

Criterio de aceptacion:

- Menu principal queda enfocado en operacion diaria.
- Configuraciones de empresa no aparecen como modulos sueltos.
- Billing no invita a pagar antes de tiempo.

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
