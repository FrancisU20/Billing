# Clients — Dominio

Estado: implementado.

## Lee Tambien Antes De Empezar

Leer estos archivos en orden antes de escribir codigo en este dominio:

| Archivo | Por que |
| --- | --- |
| `CLAUDE.md` | Reglas no negociables (seguridad, git) |
| `BACKEND.md` | Entidades tenant-scoped, locks de identificacion, idempotencia |
| `FRONTEND.md` | Patrones de pantalla, design system para `features/clients/` |
| `TENANTS.md` | `tenant_id` siempre del JWT — aislamiento por tenant |
| `AUTH.md` | Endpoints requieren rol `admin` u `owner` dentro del tenant |

## Proposito

Gestiona los compradores/clientes dentro de cada tenant. Un `Client` representa a quien
recibe una factura. Los clientes son scoped por tenant: tenant A no puede ver los clientes
de tenant B. "Consumidor Final" no es un `Client` — es un modo tributario especial del SRI.

## Componentes

- Lambda: `backend/lambdas/clients/`
- DynamoDB: tabla `clients` (tenant-scoped, convencion `TENANT#{id}`)

## Frontend

- `frontend/features/clients/`
- `frontend/app/(app)/(tenant)/clients/`
- `ClientsListScreen`/`ClientListItem`: `owner|admin` ven Editar + (Eliminar si `active` |
  Activar si `inactive`, via `clientsApi.setStatus`); `viewer` solo ve "Ver" (gated por
  `canWrite(role)` de `constants/roles.ts`). Listado, filtros (`ClientsFilters` con
  `FilterBar` compartido, ver `FRONTEND.md`) y paginacion (`ListPaginationControls` con
  total real cuando no hay `q`/`identification` activo).

## Entidades

### Client

Campos clave:

```
pk              "TENANT#{tenant_id}"
sk              "CLIENT#{client_id}"
id              UUID
tenant_id       del JWT, nunca del body
identification  cedula | RUC | pasaporte | exterior
id_type         "01" cedula | "04" RUC | "06" pasaporte | "08" exterior
name            nombre o razon social
email           opcional
phone           opcional
deleted         bool, soft delete
```

### Consumidor Final — No Es Un Client

Para facturas a consumidor final, el SRI define un modo tributario especial:

```
tipoIdentificacionComprador = "07"
identificacionComprador     = "9999999999999"
razonSocialComprador        = "CONSUMIDOR FINAL"
client_id                   = null
```

No se crea un `Client` para consumidor final. Se emite directamente con esos valores fijos.
Esto es una regla SRI, no una decision de diseno del sistema.

### Tipos De Identificacion Soportados

| Tipo | Codigo SRI | Formato |
| --- | --- | --- |
| Cedula | "01" | 10 digitos, validacion modulo 11 |
| RUC | "04" | 13 digitos |
| Pasaporte | "06" | alfanumerico libre |
| Exterior | "08" | para extranjeros sin cedula/pasaporte ecuatoriano |

La identificacion es validada por value objects en `shared/domain/value_objects/`.

### Reglas De Negocio

- La identificacion es unica **por tenant**. Mismo RUC puede existir en tenant A y tenant B.
- La unicidad se garantiza con lock transaccional: `CLIENT_IDENTIFICATION#{identification}`.
- A diferencia del RUC de tenant, el lock de cliente **se libera en soft delete**. Esto
  permite reutilizar una identificacion si el cliente se elimina y se vuelve a registrar.
- `tenant_id` siempre viene del JWT. Un cliente nunca puede asignarse a un tenant distinto
  al del caller.

## API Contract

Todos los endpoints requieren JWT + rol `admin` o `owner` dentro del tenant.

| Metodo | Ruta | Descripcion |
| --- | --- | --- |
| GET | `/clients` | lista paginada con filtros |
| POST | `/clients` | crear cliente |
| GET | `/clients/{id}` | detalle |
| PATCH | `/clients/{id}` | actualizar |
| DELETE | `/clients/{id}` | soft delete |

## DynamoDB Schema

Tabla: `clients`. Convencion `BaseRepository`:

```
PK = "TENANT#{tenant_id}"
SK = "CLIENT#{client_id}"

Identification lock:
  PK = "TENANT#{tenant_id}"
  SK = "CLIENT_IDENTIFICATION#{identification}"
  entity_type = "CLIENT_IDENTIFICATION_LOCK"
  client_id = "{uuid}"
```

GSI `identification-index`: `PK=tenant_id, SK=identification` — permite busqueda exacta Y
por prefijo de `identification` sin scan (ver abajo).

### Busqueda

- Por `identification`: `DynamoClientRepository._identification_prefix_raw()` hace Query
  sobre `identification-index` con `begins_with()` — escribir "1003" encuentra
  "1003368725" sin caminar la tabla. El metodo `get_by_identification`
  (exacto) sigue existiendo para el caso que sea, pero `list()` ya no lo usa — usa el
  prefix Query incluso cuando el usuario tipea la identificacion completa (un prefix igual
  a la cadena completa es equivalente a exacto).
- Busqueda `q` (general, nombre/razon social/identificacion por substring): v1 simple —
  camina paginas DynamoDB hasta llenar `limit` o agotar resultados. No usa full-text
  search. Para volumenes grandes esto es costoso; documentado como deuda tecnica. A
  diferencia del modo por `identification`, este SI matchea texto en cualquier posicion,
  no solo prefijo — son modos complementarios, no se reemplazan entre si.

### Total De Resultados (v2 Paginacion)

`GET /clients` devuelve `total` en el envelope (`ApiResponse.paginated(..., total=...)`) via
`DynamoClientRepository.count()` — Query tenant-scoped + `Select=COUNT`, sin transferir items.
`total` es `None`/omitido solo cuando `q` esta activo: ese filtro se resuelve en Python
(`_ClientListFilters.matches()`), no en DynamoDB, asi que un conteo DB-side no reflejaria
el resultado filtrado real. `identification` SI mantiene `total` exacto (es un prefix Query
sobre la GSI, `_identification_prefix_count()` con `Select=COUNT`) — ya no esta en la lista
de filtros que lo omiten. Ver `BACKEND.md` para el patron general.

### Salto De Pagina (v2 Paginacion)

`ClientsListScreen` usa `useEagerPagedList` (no `useCursorPagedList`): el frontend camina
TODAS las paginas de `GET /clients` para el filtro activo (acotado, catalogo por tenant) y
pagina localmente con salto real a cualquier pagina — ver `FRONTEND.md` para el detalle
del hook. No es un endpoint nuevo, es composicion del
endpoint cursor-paginado existente.

## Errores De Dominio

- `ClientNotFoundError`
- `IdentificationAlreadyRegisteredError`
- `InvalidIdentificationError`

## Edge Cases Y Trampas

- **Busqueda `q` en tablas grandes**: camina paginas DynamoDB en memoria. Con tenants de
  miles de clientes, puede ser lento y consumir muchas read units. Aceptable para v1; para
  v2 considerar OpenSearch o tabla de busqueda invertida.

- **Soft delete libera el lock**: si se elimina un cliente y se vuelve a crear con el mismo
  RUC, el sistema lo permite. Esto es diferente al comportamiento del RUC de tenant (que
  nunca se libera).

## Deuda Tecnica

- Busqueda `q` no escala con tablas grandes. Evaluar OpenSearch o tabla auxiliar si los
  tenants empiezan a tener mas de 10k clientes.
- No hay endpoint de busqueda por multiples identificaciones en batch (util para validar
  XLSX en carga masiva).
