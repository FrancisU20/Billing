# Invoices & Documents — Dominio

Estado: **pendiente de implementar**.

## Lee Tambien Antes De Empezar

Leer estos archivos en orden antes de escribir codigo en este dominio:

| Archivo | Por que |
| --- | --- |
| `CLAUDE.md` | Reglas no negociables (seguridad, git) |
| `BACKEND.md` | Patrones Lambda, outbox, idempotencia, contratos HTTP |
| `FRONTEND.md` | Estructura, design system, patrones de pantalla para el modulo de facturacion |
| `TENANTS.md` | `sri_environment` (pruebas/produccion), `plan_status`, `document_limit` por plan |
| `CLIENTS.md` | Consumidor Final NO es un Client — regla critica para el XML del SRI |
| `PLANS.md` | `document_limit`, `pruebas_monthly_docs_limit`, `dedicated_queue` |
| `ONBOARDING.md` | Certificado p12, firma XAdES-BES, entornos SRI, Secrets Manager |

## Proposito

Emision de documentos electronicos hacia el SRI de Ecuador: facturas, notas de credito,
retenciones, guias de remision. Este dominio es el nucleo del negocio.

Dos modalidades de uso:
- **Individual (portal/API)**: el tenant emite un documento a la vez.
- **Masiva (batch)**: el tenant sube un XLSX con N documentos; el sistema los procesa en cola.

## Componentes

Lambdas planificados:

| Lambda | Descripcion | Estado |
| --- | --- | --- |
| `sequences` | Contadores atomicos de numeracion SRI + establecimientos/puntos de emision | pendiente |
| `documents` | Emision individual: XML, firma XAdES-BES, envio SRI | pendiente |
| `batch_jobs` | Carga masiva XLSX: validar, encolar, trackear estado | pendiente |

## Establecimientos Y Puntos De Emision

Sub-recurso del tenant, vive junto a `sequences` (no es una lambda de "direcciones"
separada — ver decision en `ONBOARDING.md`).

```
Establishment:
  tenant_id        FK al tenant
  establecimiento  "001", "002", ... — codigo SRI de 3 digitos
  address          dirEstablecimiento (obligatorio en XML)
  puntos_emision   lista de "001", "002", ... por establecimiento
```

- El onboarding NO crea establecimientos "reales" — solo reserva el punto de pruebas
  (ver siguiente seccion). El tenant configura sus establecimientos/puntos de emision
  reales desde su dashboard antes de pasar a `sri_environment=produccion`.
- Endpoints sugeridos: `tenants/{id}/establishments` (mismo patron que `certificates`,
  dentro de la lambda `tenants` o de `sequences` — decidir al implementar segun donde
  quede menos acoplamiento).

## Secuenciales: Pruebas Vs Produccion

**Decision**: NO se agrega `ambiente` a la clave de `sequences`. En su lugar, el
onboarding reserva automaticamente:

```
establecimiento = "001"
punto_emision   = "099"   # reservado para sri_environment=pruebas
```

Todos los documentos emitidos en `pruebas` usan `001-099-*`. Los puntos de emision
`001`, `002`, ... quedan libres para cuando el tenant configure produccion. Esto evita
quemar numeracion real durante las pruebas sin tocar el schema de `sequences` definido
mas abajo (`SK = "SEQ#{establecimiento}#{punto_emision}"`).

## Secuencial Inicial (Migracion Desde Otro Sistema)

Un tenant que ya facturaba con otro proveedor no puede arrancar su secuencial en 1 — el
SRI exige continuidad. Al configurar un establecimiento/punto de emision real (no el
`099` de pruebas), el formulario debe permitir indicar el **proximo secuencial a usar**.

```
Establishment.puntos_emision[n]:
  punto_emision     "001"
  next_sequential   int  # default 1; editable solo antes del primer documento emitido
```

Regla: `next_sequential` solo es editable mientras `sequences` no tenga contador creado
para esa combinacion (antes del primer `UpdateItem ADD 1`). Una vez emitido el primer
documento real, el contador es inmutable salvo el mecanismo normal de incremento.

Servicios AWS:

- **DynamoDB tabla `documents`** — estado de cada documento
- **DynamoDB tabla `sequences`** — contadores de numeracion
- **DynamoDB tabla `batch_jobs`** — estado de cada carga masiva
- **SQS FIFO (compartida)** — cola de procesamiento batch para tenants normales
- **SQS FIFO (dedicada por tenant)** — para tenants con `plan.dedicated_queue=true`
- **S3 con Object Lock** — almacenamiento de documentos autorizados (retension 7 anos)
- **AWS Secrets Manager** — lectura del certificado p12 del tenant (provisto por ONBOARDING)

Frontend (pendiente):

- `frontend/features/documents/` — emision individual
- `frontend/features/batch-jobs/` — carga masiva XLSX

## Numeracion SRI

Formato obligatorio: `{establecimiento}-{punto_emision}-{secuencial}`
Ejemplo: `001-001-000000001`

Reglas criticas:

- El secuencial es un contador atomico DynamoDB: `UpdateItem ADD 1 RETURN NEW`. **Nunca
  `get` + incrementar + `put` — hay race condition.**
- Un tenant puede tener multiples combinaciones establecimiento/punto-emision. El contador
  es unico por combinacion `(tenant_id, establecimiento, punto_emision)`.
- El numero ya emitido **no se recicla** aunque el documento falle post-emision. El numero
  se pierde; el SRI no acepta huecos explicados despues.
- Tabla `sequences`:
  ```
  PK = "TENANT#{tenant_id}"
  SK = "SEQ#{establecimiento}#{punto_emision}"
  current = N   (contador; se incrementa con UpdateItem ADD 1)
  ```

## Estados Del Documento

```
PENDING
  -> AUTHORIZED    (SRI acepto)
  -> REJECTED      (SRI rechazo — error de negocio, no reintentable)
  -> FAILED        (error tecnico reintentable: timeout SRI, firma fallo transitoriamente)
  -> FAILED_PERMANENT   (reintentado N veces; requiere intervencion manual)
```

Regla: los errores del SRI pueden ser de dos tipos:
- **Reintentable**: timeout, servicio SRI no disponible (HTTP 5xx o timeout).
- **Permanente**: XML invalido, RUC incorrecto, numero duplicado, firma invalida.

El worker downstream debe clasificar el error antes de reintentar o marcar permanente.

## Consumidor Final — Regla Critica

Para facturas a consumidor final **NO se crea un Client**. Se emite directamente con:

```
tipoIdentificacionComprador = "07"
identificacionComprador     = "9999999999999"
client_id                   = null
```

Si el handler recibe `client_id = null` y el tipo de comprador es consumidor final,
debe usar estos valores fijos en el XML. No buscar un cliente en DynamoDB.

Esta es una regla del SRI Ecuador, no una decision de diseno del sistema.

## Firma XAdES-BES

El SRI exige firma electronica XAdES-BES con el certificado p12 del tenant.

Flujo de firma:

```
1. Construir XML del documento segun especificacion SRI
2. Leer certificado del tenant desde Secrets Manager (ARN en tenant.certificate_secret_arn)
3. Firmar XML con cryptography + lxml: XAdES-BES enveloped
4. Enviar XML firmado al WebService SRI segun tenant.sri_environment
```

La URL del WebService cambia por `sri_environment`:
- `pruebas`: `https://celcer.sri.gob.ec/...`
- `produccion`: `https://cel.sri.gob.ec/...`

El certificado es el mismo para ambos entornos. Ver `ONBOARDING.md` para las reglas
de almacenamiento del p12 en Secrets Manager.

## IVA — Tabla De Tarifas

El IVA en Ecuador ha cambiado. La tabla de tarifas debe considerar rangos de fecha:

| Periodo | Tarifa IVA |
| --- | --- |
| Hasta 2024-03-31 | 12% |
| Desde 2024-04-01 | 15% |

La tarifa correcta se determina por la fecha de emision del documento, no la fecha
del sistema al momento de procesar. Esta tabla debe mantenerse actualizada en el codigo
(`documents/domain/iva_rates.py` o similar) y puede cambiar por decreto presidencial.

## Procesamiento Masivo (Batch Jobs)

Flujo:

```
1. Tenant sube XLSX via POST /batch-jobs
2. Handler ejecuta validador XLSX sincrono (4 capas):
   a. Estructura: columnas obligatorias, tipos de dato
   b. Reglas de negocio por fila: RUC valido, IVA correcto
   c. Consistencia entre filas: totales, duplicados internos
   d. Validacion DB: clients existen, plan tiene capacidad
3. Si validacion falla: 422 con array de errores { row, col, message }
4. Si pasa: crear BatchJob (PENDING), encolar en SQS FIFO
5. Lambda worker procesa chunks de ~100 documentos
6. Cliente consulta estado: GET /batch-jobs/{id}
```

Aislamiento entre tenants en la cola:

- `MessageGroupId = tenant_id` en SQS FIFO.
- Lambda batch tiene `reserved_concurrency = 5` para no saturar el SRI.
- Tenants con `plan.dedicated_queue = true` tienen su propia SQS FIFO (ver `ONBOARDING.md`).

BatchJob entity:

```
status: PENDING | RUNNING | COMPLETED | PARTIAL_FAILURE | FAILED
total_rows: N
processed: N
authorized: N
rejected: N
failed: N
error_file_url: URL S3 del archivo de errores (si hay)
```

## Almacenamiento De Documentos Autorizados

- S3 bucket con **Object Lock** (WORM — Write Once Read Many).
- Retension legal minima: 7 anos (requerimiento SRI Ecuador).
- El XML autorizado y el RIDE (PDF) se guardan en S3 con `LegalHold` activo.
- DynamoDB guarda solo el ARN S3 del XML y RIDE; no los bytes.

## API Contract (Diseño Inicial)

```
POST /documents              — emitir documento individual
GET  /documents/{id}         — estado del documento
GET  /documents              — lista paginada con filtros

POST /batch-jobs             — iniciar carga masiva
GET  /batch-jobs/{id}        — estado del batch job
GET  /batch-jobs             — lista de batch jobs del tenant

GET  /sequences              — ver contadores de numeracion del tenant
```

Todos requieren JWT (owner o admin del tenant). El `tenant_id` viene del JWT.

## Errores De Dominio (Planificados)

- `DocumentNotFoundError`
- `CertificateNotUploadedError` — tenant intenta emitir sin certificado
- `SequenceExhaustedError` — el secuencial alcanzo el maximo del SRI (999999999)
- `SriRejectedError(code, message)` — SRI devolvio error de negocio
- `SriUnavailableError` — timeout o 5xx del SRI (reintentable)
- `InvalidDocumentError` — XML no paso validacion pre-envio
- `BatchJobNotFoundError`
- `BatchValidationError(errors: list[RowError])` — errores de validacion del XLSX

## Prerequisitos Para Empezar

Estado de prerequisitos al 2026-06-14:

1. Listo: `ONBOARDING.md` — los tenants pueden subir certificado inicial y reemplazarlo luego
   con Lambda `certificates`.
2. Pendiente: `sequences` — los contadores de numeracion deben existir antes de emitir
   cualquier documento.
3. Listo: `plans` — campos `pruebas_monthly_docs_limit`, `document_limit`,
   `dedicated_queue` y `self_service` existen.
4. Listo: `tenants` — `sri_environment` existe y el tenant nace en `testing`.

## Deuda Tecnica Anticipada

- La tabla de tarifas IVA hardcodeada en codigo debe gestionarse de forma mas robusta
  si el gobierno cambia la tarifa frecuentemente. Evaluar tabla en DynamoDB con rangos de fecha.
- El reintento de documentos `FAILED` necesita backoff exponencial y dead-letter queue para
  no saturar el SRI en caso de incidente.
- Reconocimiento de errores del SRI: el SRI Ecuador devuelve codigos de error en XML.
  Necesita un parser de respuestas y clasificacion exhaustiva reintentable vs permanente.
