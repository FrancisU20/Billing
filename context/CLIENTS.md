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

GSI `identification-index`: permite busqueda exacta por `identification` sin scan.

### Busqueda

- Exacta por `identification`: usa GSI `identification-index` directamente.
- Busqueda `q` (general): v1 simple — camina paginas DynamoDB hasta llenar `limit` o agotar
  resultados. No usa full-text search. Para volumenes grandes esto es costoso; documentado
  como deuda tecnica.

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
