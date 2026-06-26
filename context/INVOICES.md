# Invoices & Documents — Dominio

Estado: **MVP completo — Sprints 1-6 implementados** (infra, sequences, documents,
invoice_processor, frontend y notificacion al comprador con XML/RIDE).

Ultima actualizacion: 2026-06-19.

## Lee Tambien Antes De Empezar

| Archivo | Por que |
| --- | --- |
| `CLAUDE.md` | Reglas no negociables (seguridad, git, dinero con Decimal) |
| `BACKEND.md` | Patrones Lambda, outbox, idempotencia, contratos HTTP, workers SQS |
| `FRONTEND.md` | Estructura, design system, patrones de pantalla |
| `TENANTS.md` | `sri_environment`, `certificate_secret_arn`, `plan_status`, `accounting_required`, `address` |
| `CLIENTS.md` | Consumidor Final NO es un Client — regla critica para el XML del SRI |
| `PRODUCTS.md` | Lineas de factura pueden venir del catalogo, pero se persiste snapshot legal |
| `PLANS.md` | `document_limit`, `dedicated_queue` — son rate limiters de este dominio |
| `ONBOARDING.md` | Certificado p12, Secrets Manager, ciclo de vida del certificado |

## Proposito

Emision de documentos electronicos hacia el SRI de Ecuador. Nucleo del negocio.

Regla fiscal critica: si `buyer_id_type == "07"` (Consumidor Final), el sistema fuerza
`buyer_id = "9999999999999"`, `buyer_name = "CONSUMIDOR FINAL"`, `client_id = null` y
`buyer_email = null` antes de emitir. Si llegan 13 nueves con otro tipo de identificacion,
el request se rechaza. Esto evita rechazos SRI tipo "69: ERROR EN LA IDENTIFICACION DEL
RECEPTOR" por estado viejo del formulario.

Frontend: la fecha de emision se calcula con zona horaria `America/Guayaquil`, se muestra
bloqueada junto a la hora local y solo viaja al backend/SRI la fecha `YYYY-MM-DD`.

Frontend de descuentos: el facturador muestra antes de emitir la politica efectiva por
linea (`max(descuento producto, campana global activa)`), fuente (`Catalogo`/`Campana`),
monto sugerido y total sugerido. Esto es solo preview de UX; `documents` recalcula con
`Decimal` y valida el techo real en backend antes de persistir.

**Alcance MVP (Sprint 1-6):** Factura electronica (tipo 01), emision individual,
multiples establecimientos desde el primer dia, XML/RIDE descargables y entrega automatica
al comprador con XML autorizado + RIDE adjuntos cuando existe `buyer_email`.

Dashboard/operabilidad: `GET /documents/summary` devuelve el resumen del mes civil Ecuador
para el tenant autenticado (`issued_count`, `authorized_count`, `rejected_count`,
`failed_count`, `pending_count`, `processing_count`, `authorized_total`). Usa Query sobre
`tenant-docs-index` acotado al mes y suma solo documentos autorizados para el total
facturado visible. Tambien incluye `document_limit`/`is_unlimited`: el handler resuelve
tenant+plan igual que `_emit` (mismo `DynamoPlanReader`, mismo criterio
`pruebas_monthly_docs_limit` vs `document_limit` segun `sri_environment`) y se lo pasa a
`GetDocumentsSummaryUseCase`, que lo adjunta al `DocumentSummary` inmutable sin que el
repositorio de documents conozca nada de planes. Si el plan no se puede resolver
(`ValidationError`, ej. desactivado por superadmin con tenants aun suscritos),
`document_limit` queda en `null` y el resto del summary se devuelve igual — no se cae todo
el endpoint por esa causa.

El mismo `summary_this_month()` tambien devuelve `daily_issued` (lista `{date, count}`, un
punto por dia civil Ecuador entre `period_start` y `period_end`, con `count=0` en los dias
sin actividad) y `top_clients` (top 5 `{client_id, name, total}` por monto AUTORIZADO del
mes, excluyendo documentos sin `client_id` — "Consumidor Final" nunca entra al ranking).
Ambos se acumulan en el mismo loop que ya pagina el GSI `tenant-docs-index`: cero lecturas
adicionales, `name` es el `buyer_name` ya snapshoteado en el documento (no se vuelve a
consultar `clients`). Usados por el dashboard tenant (ver `FRONTEND.md`).

**Fuera de alcance MVP:** retencion (07), batch masivo XLSX. Nota de credito (04) ya esta
implementada (ver seccion siguiente). Esos dos se disenan en sprints posteriores pero la
arquitectura actual los soporta sin migraciones.

### Anulacion De Documentos (Historico) — Marcado Local, Reemplazado Por Nota De Credito

El SRI **no expone un webservice** para anular comprobantes electronicos (a diferencia de
recepcion/autorizacion, que si son SOAP) — confirmado contra 3 fuentes independientes
(NMS legal, Facturero Movil, soporte Contifico/Siigo). Es un tramite manual: el
contribuyente entra al portal SRI en linea con sus propias credenciales (o usa el
Facturador SRI), pide la anulacion ahi, y el sistema de facturacion solo debe reflejar
el resultado despues.

Por eso `POST /documents/{id}/annul` (`AnnulDocumentUseCase` +
`DynamoDocumentsRepository.annul()`) nunca llamo a ningun servicio del SRI — solo marcaba
`status=ANNULLED` con auditoria, asumiendo que el tramite manual ya se habia hecho. Esto
se **deprecio (2026-06-24)**, no se borro: `annul_document.py`, la ruta
`POST /documents/{id}/annul`, `DocumentStatus.ANNULLED` y los errores
`ConsumerFinalCannotBeAnnulledError`/`AnnulmentWindowExpiredError` quedan en el codigo para
que los documentos ya anulados antes de este cambio sigan renderizando bien
(`DocumentDetailScreen.tsx` todavia muestra el banner "Anulado" para esos), pero **la UI ya
no los alcanza** — ningun flujo nuevo navega a esa ruta. El reemplazo real (que si llega al
SRI) es Nota de Credito, seccion siguiente.

### Nota De Credito (04) — Implementada (2026-06-24)

Reemplaza la anulacion local como el mecanismo "real" de cerrar el efecto tributario de una
factura: es un comprobante electronico mas, mismo flujo SOAP completo (firma XAdES-BES +
`recepcion`/`autorizacion`) que Factura — a diferencia de la anulacion local, esto si llega
al SRI.

**Diseno de UX (revisado 2026-06-26):** la version inicial (2026-06-24) usaba una sola
pantalla con dos entradas (`locked=true`/`false`). Se reemplazo por dos flujos separados
tras el primer uso real, porque "anular" no necesita revisar lineas/comprador y "nota de
credito parcial" no debia vivir como boton dentro de Documentos:
- **"Anular factura"** (en el menu de 3 puntos del listado y en el detalle de
  `DocumentsListScreen.tsx`/`DocumentDetailScreen.tsx`) → abre `AnnulInvoiceModal.tsx`, un
  modal con un **unico campo visible: motivo**. Las lineas se calculan en background al
  100% con `defaultCreditNoteFormValues(document, true)` (mismo helper que usaba la
  pantalla vieja) y se emiten directo via `documentsApi.emitCreditNote()` sin navegar. No
  hay pantalla intermedia.
- **Nota de credito parcial** vive en un **modulo independiente** del menu principal
  ("Notas de credito", `CreditNoteInvoicesListScreen.tsx`, ruta
  `Routes.tenant.creditNotes` → `/credit-notes`) que lista facturas elegibles
  (`doc_type='01'`, `status='AUTHORIZED'`, mismo filtro que antes resolvia
  `InvoicePickerModal`). Tocar "Acreditar" en una fila navega a
  `EmitCreditNoteScreen.tsx` (`documents/credit-note.tsx`) con `parent` preseleccionado —
  esa pantalla ya **no** soporta `locked`, quedo dedicada solo al flujo editable parcial.
  El boton "Nota de credito" se quito de Documentos (listado y detalle).
- `InvoicePickerModal.tsx` sigue existiendo solo como fallback de
  `EmitCreditNoteScreen.tsx` si se llega a la ruta sin `parent` (deep link directo); ya no
  es el camino principal para elegir factura.

**Elegibilidad** (`features/documents/utils.ts::getCreditNoteBlockReason`): solo
`doc_type === '01'` (una NC no puede acreditar otra NC) y `status === 'AUTHORIZED'`. **Sin
excepcion de Consumidor Final ni ventana de plazo** — esas dos restricciones eran
especificas del tramite manual de anulacion en linea (Res. NAC-DGERCGC25), no de las Notas
de Credito. Esto es un fix real: antes no se podia anular una factura a Consumidor Final;
ahora si se puede acreditar con NC. `RowActionsMenu`
(`disabled`/`disabledReason`) sigue mostrando la accion atenuada con el motivo en vez de
ocultarla cuando no aplica.

**Backend:**
- `Document.related_document_id`/`credit_note_reason` (nuevos campos opcionales, solo
  `doc_type="04"`). El resto de los datos de la factura padre (`numDocModificado`,
  `fechaEmisionDocSustento`) se leen en vivo via `related_document_id` en vez de
  duplicarse — son inmutables post-autorizacion.
- `EmitCreditNoteUseCase` (`use_cases/emit_credit_note.py`) — **no** es una rama de
  `EmitDocumentUseCase`: las lineas no se resuelven contra el catalogo de productos
  vigente, se copian de los snapshots ya persistidos de la factura padre
  (`parent.lines`), escalando proporcionalmente por `cantidad_acreditada/cantidad_original`
  (incluye descuento e IVA — nunca se re-deriva la tasa de IVA aplicable, se escala el
  monto ya calculado de la linea original). Solo permite reducir cantidad, nunca agregar
  lineas ni cambiar precios. `domain/totals.py::aggregate_line_totals` extrae la suma de
  IVA por linea, compartida con `EmitDocumentUseCase._compute_totals` (refactor sin cambio
  de comportamiento).
- Secuenciales por `doc_type`: `ISequencesPort.reserve_next(tenant_id, serie, doc_type)`.
  SK `SEQ#{estab}#{punto}` sin cambios para `doc_type="01"` (compatibilidad); para otros
  tipos, `SEQ#{estab}#{punto}#{doc_type}` con **bootstrap perezoso** (auto-creacion en el
  primer uso, arranca en 1) — sin tocar la UI de establecimientos/puntos de emision.
  **Limitacion deliberada v1:** si un tenant ya emitia NC por otro sistema antes de Wali,
  no hay forma de fijar un secuencial inicial distinto (mismo espiritu que la limitacion ya
  documentada para `01`).
- `xml_builder.py`: `build_credit_note_xml(document, tenant, parent)` — root
  `<notaCredito>`, body `<infoNotaCredito>` (codDocModificado/numDocModificado/
  fechaEmisionDocSustento/motivo, sin bloque `<pagos>`). Comparte
  `_build_total_con_impuestos`/`_build_detalle_common` con `build_invoice_xml`, pero **no**
  comparte la etiqueta de codigo de linea: `_build_detalles_factura` usa
  `codigoPrincipal`/`codigoAuxiliar` y `_build_detalles_nota_credito` usa
  `codigoInterno`/`codigoAdicional` — el XSD `notaCredito` del SRI rechaza
  `codigoPrincipal` (bug real, fijo 2026-06-26: la primera version usaba una sola
  `_build_detalles` con `codigoPrincipal` para ambos doc_type, y el SRI rechazaba **toda**
  NC/anulacion con "Invalid content was found starting with element 'codigoPrincipal'").
- `ride_builder.py`: titulo "NOTA DE CRÉDITO No. ..." + referencia "Modifica a: Factura
  ..." cuando hay `parent`.
- `summary_this_month`: las NC **restan** de `authorized_total` (ingreso neto) en vez de
  sumarse como factura — bug real que se hubiera introducido si no se corregia antes de que
  existieran NCs. Nuevos campos `DocumentSummary.credit_notes_count`/`credit_notes_total`
  para transparencia. `top_clients` queda solo-facturas en v1 (decision, no deuda — evita
  rankings negativos).
- `GET /documents?doc_type=` — filtro opcional, usado por `InvoicePickerModal` para no
  mostrarse a si misma una NC ya autorizada al buscar facturas para acreditar.

**Frontend:** `InvoicePickerModal.tsx` (selector de factura, modelado sobre
`ClientPickerModal`/`PickerModal`, sin "crear rapido"); `BuyerReadOnlySection.tsx`
(comprador siempre viene de la factura padre, nunca se re-elige); `creditNoteForm.ts`
(helpers puros: `defaultCreditNoteFormValues`, `creditNoteFormValuesToInput`,
`computeCreditNoteTotals` — replica en cliente la misma logica de escalado proporcional que
el backend, solo para preview).

**Validacion contra XSD oficial (mitigado 2026-06-26):** se agrego
`sri_xsd/nota_credito_v1.xsd` (descargado de sri.gob.ec, "XML y XSD Nota de Credito.zip",
version 1.1.0 — a diferencia de `factura_v1.xsd` que es 1.0.0 reusado, este coincide
exacto con `_SCHEMA_VERSION`) y un test
(`test_xsd_compliance.py::NotaCreditoXsdComplianceTests`) que valida la NC firmada contra
ese esquema, mismo patron que ya existia para Factura. Esto se agrego justamente porque
el bug de `codigoPrincipal` (ver arriba) **no** lo detectaban los tests de estructura
propios (`test_xml_builder.py`) — solo comparaban contra si mismos, nunca contra el
esquema real del SRI; se confirmo manualmente que el test nuevo reproduce el mismo error
exacto que dio el SRI en produccion si se revierte el fix. Sigue existiendo un riesgo
residual menor: el XSD valida estructura/tipos, no reglas de negocio del propio servicio
SOAP del SRI (eso solo se confirma probando contra el ambiente de pruebas real,
`celcer.sri.gob.ec`).

## Lambdas Y Responsabilidades

| Lambda | Tipo | Responsabilidad |
| --- | --- | --- |
| `sequences` | HTTP | CRUD establecimientos + puntos de emision. NO expone contadores internos. |
| `documents` | HTTP | Emision individual: valida, reserva secuencial, computa access\_key, encola; expone descarga XML/RIDE y marcado local de anulacion. |
| `invoice_processor` | SQS worker | Firma XAdES-BES, envio SRI SOAP, polling de autorizacion, genera RIDE, guarda en S3. |

`batch_jobs` es un Lambda futuro (no MVP). La tabla `batch_jobs` se crea en el Sprint 1
de infra para no hacer migraciones despues, pero el Lambda no se implementa hasta
que se requiera.

## Arquitectura De Procesamiento

### Por que dos colas separadas para SIGN y POLL

Con una sola cola mixta, los mensajes POLL (que son el 90% del volumen despues del primer
dia en produccion) compiten por concurrencia con los SIGN. Un pico de POLL saturaria los
slots de Lambda dejando SIGN en espera. Con colas separadas cada flujo tiene su propio
`reserved_concurrency` y no se bloquean entre si.

### Por que SQS Standard (no FIFO)

El secuencial de cada documento se asigna **en el request HTTP** antes de encolar. El
worker recibe el documento ya numerado — no necesita procesar mensajes en orden. SQS
Standard tiene throughput ilimitado y es mas barato que FIFO ($0.40 vs $0.50/millon).

FIFO con MessageGroupId solo se justificaria si el numero de secuencia dependiera del
orden de llegada al worker. No es el caso aqui.

### Configuracion de colas y concurrencia

| Cola | Tipo | Tenants | `batch_size` ESM | `reserved_concurrency` Lambda | Razon |
| --- | --- | --- | --- | --- | --- |
| `invoice-sign` | Standard compartida | Pequeños | 10 | 30 | Rate limit sobre cola mixta; impide monopolio |
| `invoice-poll` | Standard compartida | Pequeños | 10 | 20 | Poll es mas liviano que sign |
| `invoice-sign-{tenant_id}` | Standard dedicada | Enterprise | 50 | 10 por cola | batch\_size=50 habilita 1 llamada SOAP por 50 docs |
| `invoice-poll-{tenant_id}` | Standard dedicada | Enterprise | 50 | 5 por cola | Poll enterprise con aislamiento total |

Todas las colas tienen DLQ (`max_receive_count=5`) y alarma CloudWatch al primer mensaje
en DLQ.

### Por que batch\_size=50 en enterprise importa

```
10,000 docs/dia ÷ 50 batch = 200 llamadas SOAP a SRI/dia
10,000 docs/dia ÷  1 batch = 10,000 llamadas SOAP/dia
```

50x menos llamadas SOAP. Menos latencia de red, menos carga en el SRI, menos costo Lambda.

Para clientes pequeños (25 docs/dia), cada SQS batch de 10 mensajes tiene 10 tenants
distintos = 10 llamadas SOAP con 1 doc c/u. Aceptable: 0.29 docs/segundo no requiere
batching entre tenants.

### Tiempo de autorizacion enterprise (10,000 docs en burst)

```
Firma XAdES-BES 50 docs:    7.5s  (150ms/doc a 1GB ARM64)
Llamada SOAP recepcion SRI: 1.5s
Total por invocacion:       ~10s

200 invocaciones / 10 concurrent = 20 rondas × 10s = 200s
Polling (30s delay + 0.5s respuesta SRI): ~35s adicionales

Total PENDING → AUTHORIZED para los 10,000 docs: ~4-5 minutos
```

Autorizacion el mismo dia garantizada con holgura, incluso si SRI es lento (10s/llamada
= 7 minutos total).

### Colas enterprise dedicadas — cuando se crean

Las colas dedicadas se crean via endpoint superadmin `POST /tenants/{id}/dedicated-queue/provision`
(pendiente de implementar, ver `TENANTS.md`). Se registran en `Tenant.dedicated_queue_arn`.
Hasta que se provisionan, el tenant enterprise usa la cola compartida.

## Establecimientos Y Puntos De Emision

Sub-recurso del tenant. Vive en la tabla `sequences` (mismo dominio que los contadores).

### Entidades

```
Establecimiento (implementado en Sprint 2 — sin `address` ni `is_active`,
a diferencia del diseño original de esta sección):
  code              "001", "002", ...    codigo SRI de 3 digitos
  label             "Matriz", "Sucursal Norte"
  emission_points   lista embebida (max ~10 en la practica):
    [
      { "code": "001", "label": "Caja 1",  "initial_sequential": 1 },
      { "code": "099", "label": "Pruebas", "initial_sequential": 1 }  ← auto-creado
    ]
```

**Deuda real (Sprint 4):** `dirEstablecimiento` es obligatorio en el XSD del SRI
(`infoFactura`, justo despues de `fechaEmision`) — sin el, el SRI rechaza con
`ARCHIVO NO CUMPLE ESTRUCTURA XML` (codigo 35), confirmado contra
`celcer.sri.gob.ec` el 2026-06-18. Como `Establecimiento` no guarda una direccion
propia, `xml_builder.py` reusa `tenant.address` (la matriz) para todos los
establecimientos. Si se necesita una direccion real por sucursal, agregar
`address` a `Establecimiento` (migracion + schema + UI de `EstablishmentCard`).

Los puntos de emision viven como array en el item del establecimiento, no como items
separados. Se leen siempre junto al establecimiento, nunca de forma independiente.

### Punto de pruebas 001-099 — auto-creacion

Al completarse la carga del primer certificado p12 (evento `CertificateUploadedEvent`
procesado por el worker), el sistema auto-crea:

```
Establecimiento 001 + punto de emision 099
SEQ#001#099 con current=0, initial=0
```

El punto 099 es una convencion de este sistema (no del SRI). Todos los documentos
emitidos en `sri_environment=testing` usan la serie `001099`. Los puntos 001, 002, ...
quedan libres para produccion.

El tenant NO puede crear manualmente un punto 099. El handler debe rechazarlo.

### Migracion desde otro proveedor

Un tenant que ya facturaba fuera del sistema necesita continuar el secuencial desde donde
quedo. El formulario de alta de punto de emision acepta `initial_sequential`:

```
POST /tenants/{id}/establishments/{code}/emission-points
Body: { "code": "001", "label": "Caja principal", "initial_sequential": 5000 }
```

Esto crea `SEQ#001#001` con `current=4999, initial=4999`. El primer `UpdateItem ADD 1`
retorna 5000. Correcto.

Regla de bloqueo: `initial_sequential` solo es editable si `current == initial`
(ningun documento emitido en esa serie aun). Una vez que `current > initial`, el endpoint
PATCH devuelve `SEQUENCE_ALREADY_USED`.

## Numeracion SRI

Formato obligatorio en XML: `{estab}-{punto}-{secuencial}`
Ejemplo: `001-001-000000001`

### Asignacion en el request HTTP, no en el worker

El secuencial se asigna **sincrono, en el handler HTTP**, antes de encolar. El worker
recibe el documento ya numerado y no tiene que coordinar orden.

```
HTTP POST /documents:
  1. Validar request + limites del plan
  2. DynamoDB UpdateItem ADD 1 en SEQ#estab#punto → obtiene N
  3. Computar access_key (49 digitos) usando N
  4. Guardar documento con status=PENDING y access_key en DynamoDB
  5. Encolar mensaje SIGN a SQS: { document_id, tenant_id }  (sin XML — ver abajo)
  6. Retornar 202 + { document_id, access_key, sequential: N }
```

El XML se construye en el worker (no se serializa en SQS ni en DynamoDB). El mensaje
SQS solo lleva los IDs. El worker hace `GetItem` del documento y construye el XML
desde los datos persistidos.

### Implementacion del contador atomico

```python
# sequences/infra/sequences_repository.py
def reserve_next(self, tenant_id: str, serie: str) -> int:
    estab, punto = serie[:3], serie[3:]
    try:
        resp = self._table.update_item(
            Key={"pk": f"TENANT#{tenant_id}", "sk": f"SEQ#{estab}#{punto}"},
            UpdateExpression="ADD #cur :one",
            ConditionExpression="#cur < :max",
            ExpressionAttributeNames={"#cur": "current"},
            ExpressionAttributeValues={":one": 1, ":max": 999_999_999},
            ReturnValues="UPDATED_NEW",
        )
        return int(resp["Attributes"]["current"])
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            raise SequenceExhaustedError(serie) from exc
        raise
```

La tabla `sequences` crea el item de contador cuando se da de alta el punto de emision
(con `current=initial_sequential - 1`, o `current=0` si arranca en 1). El `ADD 1` con
`ConditionExpression` funciona sin necesitar `attribute_not_exists`.

### Reglas de numeracion

- El numero emitido **no se recicla** aunque el documento falle despues. El numero se
  pierde; el SRI no penaliza huecos pero tampoco los acepta si son "explicados" post-hoc.
- Un tenant puede tener N combinaciones establecimiento/punto. El contador es unico por
  combinacion.
- El secuencial maximo es 999,999,999 (9 digitos). Al llegar al limite, `SequenceExhaustedError`.

### Limite por plan como rate limiter implicito

Antes de reservar el secuencial, el handler valida que el tenant no haya superado su
`plan.document_limit` mensual. Si lo supero: 422 `DOCUMENT_LIMIT_REACHED`. Esto previene
que un cliente de plan pequeño colapse la cola compartida con miles de mensajes.

## DynamoDB Schema

### Tabla `sequences`

PK = `"TENANT#{tenant_id}"`, SK variable segun tipo de item.

```
# Establecimiento
SK = "ESTAB#001"
entity_type      = "ESTABLISHMENT"
code             = "001"
name             = "Matriz"
address          = "Av. Principal 123, Quito"
is_active        = true
emission_points  = [
  { "code": "001", "label": "Caja 1",  "initial_sequential": 1 },
  { "code": "099", "label": "Pruebas", "initial_sequential": 1 }
]
created_at       = ISO8601

# Contador de secuencial
SK = "SEQ#001#001"
entity_type      = "INVOICE_SEQUENCE"
serie            = "001001"
current          = N      ← contador atomico, solo se escribe con UpdateItem ADD
initial          = N      ← valor al crear el punto; para detectar primer uso
```

No hay GSI en esta tabla. Los accesos son siempre por PK = `TENANT#{tenant_id}`:
- `Query SK begins_with "ESTAB#"` → listar establecimientos
- `GetItem SK = "SEQ#001#001"` → leer contador (no se usa; solo UpdateItem ADD)

### Tabla `documents`

PK = `"TENANT#{tenant_id}"`, SK = `"DOC#{document_id}"`.

```
entity_type              = "INVOICE"
document_id              = UUID
doc_type                 = "01"                     ← Factura
status                   = "PENDING" | "PROCESSING" | "AUTHORIZED" | "REJECTED"
                           | "FAILED" | "FAILED_PERMANENT"
serie                    = "001001"                  ← establ + punto concatenados
sequential               = 1                         ← entero, asignado en HTTP
access_key               = "..."                     ← 49 digitos, computado en HTTP

# Datos del comprador (snapshot en el momento de emision — no FK live)
client_id                = UUID | null               ← null si Consumidor Final
buyer_id_type            = "04"|"05"|"06"|"07"|"08" ← tipo identificacion SRI
buyer_id                 = "9999999999999"           ← "9999999999999" si CF
buyer_name               = "Consumidor Final" | nombre real
buyer_email              = str | null

# Notificacion al comprador (Sprint 6 implementado)
buyer_notification_status = null | "PENDING" | "SENDING" | "SENT" | "SKIPPED_NO_EMAIL" | "FAILED"
buyer_notified_at         = ISO8601 | null
buyer_notification_error  = str | null

# Fechas
issued_at                = ISO8601                  ← fecha de emision (en el XML)
created_at               = ISO8601
updated_at               = ISO8601
authorized_at            = ISO8601 | null
rejected_at              = ISO8601 | null

# SRI
authorization_number     = str | null               ← numero de autorizacion SRI
sri_environment          = "testing" | "production"
xml_s3_key               = "tenants/{id}/docs/{year}/{doc_id}.xml" | null
ride_s3_key              = "tenants/{id}/docs/{year}/{doc_id}.pdf" | null
sri_errors               = [{"code": "...", "message": "..."}] | null

# Totales (Decimal como string exacto)
subtotal                 = "100.00"
total_discount           = "0.00"
iva_15                   = "15.00"
iva_5                    = "0.00"
iva_0                    = "0.00"
total                    = "115.00"
payment_method           = "01"                     ← efectivo por defecto

# Lineas de detalle (embebidas; no items separados)
lines = [
  {
    "code":        str,
    "description": str,
    "quantity":    Decimal str,
    "unit_price":  Decimal str,
    "discount":    Decimal str,
    "subtotal":    Decimal str,
    "iva_rate":    "15" | "5" | "0" | "EXENTO",
    "iva_amount":  Decimal str,
    "total":       Decimal str
  }
]

# Resiliencia
retry_count              = 0                        ← incrementa en FAILED; max 5
deleted                  = false
```

GSI: `tenant-docs-index`
- PK = `tenant_id` (atributo denormalizado), SK = `created_at`
- Proyeccion: ALL
- Uso: listar documentos de un tenant ordenados por fecha, con `FilterExpression` por status

No se necesita GSI de status global porque el polling de SRI se maneja via SQS delay,
no via scan de documentos PROCESSING.

### Tabla `batch_jobs`

PK = `"TENANT#{tenant_id}"`, SK = `"JOB#{job_id}"`.

```
entity_type   = "BATCH_JOB"
job_id        = UUID
status        = "PENDING" | "RUNNING" | "COMPLETED" | "PARTIAL_FAILURE" | "FAILED"
total_rows    = N
processed     = N
authorized    = N
rejected      = N
failed        = N
error_file_s3 = "tenants/{id}/batch-errors/{job_id}.json" | null
created_at    = ISO8601
updated_at    = ISO8601
```

Tabla creada en Sprint 1 de infra. Lambda `batch_jobs` se implementa en sprint posterior
al MVP.

## S3 — Almacenamiento Legal

Bucket: `codelabs-billing-{env}-documents`

```python
# infra/stacks/storage_stack.py (nuevo stack)
s3.Bucket(
    object_lock_enabled=True,
    object_lock_default_retention=s3.ObjectLockRetention.governance(
        duration=Duration.days(365 * 7 + 2)   # 7 anios + margen
    ),
    lifecycle_rules=[s3.LifecycleRule(
        transitions=[
            s3.Transition(storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                          transition_after=Duration.days(30)),
            s3.Transition(storage_class=s3.StorageClass.GLACIER_INSTANT_RETRIEVAL,
                          transition_after=Duration.days(90)),
        ]
    )],
    block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
    removal_policy=RemovalPolicy.RETAIN,
)
```

Estructura de prefijos S3:

```
tenants/{tenant_id}/docs/{year}/{document_id}.xml   ← XML firmado autorizado
tenants/{tenant_id}/docs/{year}/{document_id}.pdf   ← RIDE PDF
tenants/{tenant_id}/batch-errors/{job_id}.json      ← errores de batch (futuro)
```

Reglas:
- DynamoDB guarda solo el S3 key, no los bytes.
- El XML y RIDE se escriben con `LegalHold=ON` al momento de guardar. No se pueden
  sobreescribir ni borrar durante los 7 anios de retension.
- Solo `AUTHORIZED` genera archivos en S3. Documentos `REJECTED` no van a S3.
- Descarga XML/RIDE: pre-signed URL con TTL 15 minutos (`GET /documents/{id}/xml` y
  `GET /documents/{id}/ride`). Disponible tanto en `DocumentDetailScreen` como en
  `DocumentListItem` (`RowActionsMenu`) cuando existen `xml_s3_key`/`ride_s3_key`; si no
  hay ninguna accion disponible el kebab no se renderiza — ver "Acciones de fila" en
  `FRONTEND.md`.

Estimacion de costo de almacenamiento para un enterprise de 10,000 docs/dia:
```
60KB promedio (XML + RIDE) × 10,000 × 365 × 7 = ~1.5 TB en 7 anios
S3-IA (despues de 30 dias): $0.0125/GB ≈ $8/mes/enterprise
S3 Glacier (despues de 90 dias): $0.004/GB para archivos maduros
```

## Lambda invoice\_processor — Diseno Interno (Sprint 4, implementado)

ARM64, 1 GB de memoria, timeout 120s. La estimacion de "Tiempo de autorizacion
enterprise" (mas abajo) muestra que incluso el caso mas pesado (firma+SOAP de un
batch de 50 docs) toma ~10s por invocacion — 120s deja margen amplio incluyendo el
read timeout de 60s configurado en `sri_client.py` ante un SRI lento. El timeout de
la funcion debe ser `<=` el `visibility_timeout` de su cola SQS (`QueuesStack`) o
AWS rechaza el `EventSourceMapping` al crearlo — paso real en el deploy del Sprint 5
(`Queue visibility timeout: 360 seconds is less than Function timeout: 900 seconds`),
cuando el timeout original (15 min, sobreestimado) no calzaba con la cola heredada
de Sprint 1 (360s). Las colas `invoice-sign`/`invoice-poll` ahora usan 720s
(6× este timeout, mismo patron que el resto de colas del proyecto).

**Desplegado como dos funciones CDK, mismo codigo**: `invoice-processor-sign`
(suscrita a `invoice-sign`) e `invoice-processor-poll` (suscrita a `invoice-poll`).
El mismo `handler.handler` rutea por `type` en ambas — ver `infra/stacks/api_stack.py`.

**Sin `reserved_concurrent_executions`** (diseño original preveia 30/SIGN y 20/POLL
para diferenciar concurrencia por funcion, ya que no se puede variar por ESM). La
cuenta AWS de este proyecto tiene el limite de Lambda en `sa-east-1` en el piso por
defecto (**10 ejecuciones concurrentes TOTALES en la cuenta**, no las 1000
estandar — nunca se pidio el aumento). Cualquier reserva > 0 baja el unreserved pool
por debajo del minimo de 10 y CloudFormation falla (`CREATE_FAILED:
"decreases account's UnreservedConcurrentExecution below its minimum value of
[10]"`) — paso real en el deploy del Sprint 4 a dev, con rollback automatico limpio.
dev/staging/prod comparten la misma cuenta AWS (`infra/config/*.yaml`, `account`
resuelto via `CDK_DEFAULT_ACCOUNT`), asi que aplica a los 3 entornos. Retomar la
diferenciacion 30/20 si se pide un quota increase a AWS para Lambda concurrent
executions en `sa-east-1`.

### p12 cacheado a nivel de modulo

```python
# invoice_processor/infra/certificate_loader.py — fuera del handler
_cache: dict[str, tuple[RSAPrivateKey, Certificate]] = {}

def load_certificate(secret_arn: str) -> tuple[RSAPrivateKey, Certificate]:
    if secret_arn in _cache:
        return _cache[secret_arn]
    secret = get_secret_json(secret_arn)  # {"p12_b64": ..., "password": ...}
    private_key, certificate, _ = pkcs12.load_key_and_certificates(...)
    _cache[secret_arn] = (private_key, certificate)
    return private_key, certificate
```

Lambda reutiliza el contenedor entre invocaciones. El certificado carga una vez por cold
start. Cero llamadas a Secrets Manager por documento. IAM: `secretsmanager:GetSecretValue`
de solo lectura sobre `/codelabs-billing/{env}/tenant/*` (distinto del grant
Create/Put que ya tienen `certificates`/`onboarding`).

### Routing por tipo de mensaje

```python
# invoice_processor/handler.py
def _process_record(record: dict) -> None:
    body = json.loads(record["body"])
    if body["type"] == "SIGN":
        _handle_sign(body)
    elif body["type"] == "POLL":
        _handle_poll(body)
```

### Mensaje SIGN

```json
{ "type": "SIGN", "document_id": "...", "tenant_id": "..." }
```

Flujo:

```
1. GetItem documento de DynamoDB → cargar todos los datos
2. GetItem tenant de DynamoDB → obtener certificate_secret_arn, sri_environment, address
3. Construir XML Factura 01 (xml_builder.py)
4. Cargar p12 del tenant (cacheado)
5. Firmar XML con XAdES-BES (signing.py)
6. Acumular hasta batch_size documentos del mismo tenant (ya asegurado por cola dedicada
   para enterprise; para pequeños se envian de a 1 por RUC distinto)
7. POST SOAP RecepcionComprobantesOffline — batch de hasta 50 docs del mismo RUC
8. Parsear respuesta:
   - RECIBIDA: UpdateItem status=PROCESSING → encolar POLL (DelaySeconds=30)
   - DEVUELTA:  clasificar errores SRI (permanente vs reintentable)
               permanente → status=REJECTED, sri_errors
               reintentable → status=FAILED, retry_count++
```

### Mensaje POLL

```json
{ "type": "POLL", "document_id": "...", "access_key": "...",
  "tenant_id": "...", "attempt": 1 }
```

Flujo:

```
1. GET SOAP AutorizacionComprobantesOffline (access_key)
2. Parsear respuesta:
   AUTORIZADO   → generar RIDE PDF (ride_builder.py)
                  → PUT XML firmado en S3 (con LegalHold)
                  → PUT RIDE en S3 (con LegalHold)
                  → UpdateItem status=AUTHORIZED + authorization_number + xml_s3_key + ride_s3_key
                  → outbox event DocumentAuthorizedEvent (email al emisor)
                  → outbox event DocumentBuyerNotificationRequestedEvent
                    (worker rehidrata el documento, lee XML/RIDE desde S3 y envia
                     email al comprador con adjuntos; idempotente por estado)

   RECHAZADO    → UpdateItem status=REJECTED + sri_errors
                  → outbox event DocumentRejectedEvent (email al tenant)

   EN_PROCESO   → if attempt < 5:
                    delay = min(30 * 2**attempt, 600)   # backoff: 30s, 60s, 120s, 240s, 600s
                    encolar POLL con attempt+1 y DelaySeconds=delay
                  else:
                    UpdateItem status=FAILED_PERMANENT
                    outbox event DocumentFailedPermanentEvent
```

### Modulos internos del invoice\_processor

```
invoice_processor/
  handler.py              # sqs_handler.py pattern, rutea SIGN/POLL, DI de cold start
  ports.py                 # ABCs: ISriClient, IDocumentStorage, IQueuePublisher
  events.py                 # DocumentAuthorizedEvent / BuyerNotificationRequested / Rejected / FailedPermanent
  xml_builder.py            # puro: construye XML Factura 01 segun spec SRI v1.1.0
  signing.py                 # XAdES-BES enveloped (cryptography + lxml), RSA-SHA1/SHA1/C14N 1.0
  sri_client.py               # SOAP client (urllib3): RecepcionComprobantesOffline + AutorizacionComprobantesOffline
  sri_error_classifier.py     # puro: codigo SRI -> PERMANENT | RETRYABLE
  ride_builder.py              # genera PDF RIDE con reportlab (texto, sin barcode/logo en MVP)
  use_cases/
    sign_document.py            # SignDocumentUseCase
    poll_document.py            # PollDocumentUseCase
  infra/
    certificate_loader.py        # carga + cachea p12 (Secrets Manager)
    s3_document_storage.py       # implementa IDocumentStorage (LegalHold=ON)
    sqs_event_publisher.py       # implementa IQueuePublisher (enqueue POLL + publish email events)
```

`IDocumentsRepository` (documents lambda) y `DynamoTenantRepository` (tenants lambda)
se reusan directamente — sin puerto propio, "acceso directo controlado" por
`BACKEND.md`, mismo patron que ya usa `documents/handler.py` para leer tenants.

## Flujo Completo End-To-End

```
Tenant (API/Frontend)
  │
  └► POST /documents
       │ valida body + limites plan
       │ reserve_next(tenant_id, serie)  → N  [DynamoDB ADD atómico]
       │ compute_access_key(...)          → 49 dígitos
       │ save(Document(status=PENDING))  [DynamoDB Put]
       │ sqs.send("SIGN", document_id)   [SQS invoice-sign o invoice-sign-{id}]
       └► 202 { document_id, access_key }

  SQS invoice-sign
  │
  └► invoice_processor (SIGN handler)
       │ fetch Document + Tenant
       │ build XML (xml_builder)
       │ sign XML (signing, p12 cacheado)
       │ SOAP RecepcionComprobantesOffline (batch hasta 50 del mismo RUC)
       │ if RECIBIDA:
       │   update status=PROCESSING
       │   sqs.send("POLL", document_id, attempt=1, delay=30s)
       └► if DEVUELTA → REJECTED o FAILED

  SQS invoice-poll (con delay 30s)
  │
  └► invoice_processor (POLL handler)
       │ SOAP AutorizacionComprobantesOffline
       ├► AUTORIZADO:
       │    generate RIDE PDF
       │    PUT XML + RIDE → S3 (Object Lock, LegalHold)
       │    update status=AUTHORIZED + s3_keys
       │    outbox → DocumentAuthorizedEvent → email al emisor
       │    outbox → DocumentBuyerNotificationRequestedEvent → email al comprador
       ├► RECHAZADO:
       │    update status=REJECTED + sri_errors
       │    outbox → DocumentRejectedEvent → email
       └► EN_PROCESO (PPR):
            if attempt < 5 → re-enqueue POLL (backoff exponencial)
            else           → FAILED_PERMANENT + alert
```

## Estructura De Archivos Backend

```
backend/lambdas/
  sequences/
    handler.py
    schemas.py
    domain/
      entities.py         # Establishment, EmissionPoint, InvoiceSequence
      commands.py
      errors.py           # SequenceExhaustedError, SequenceAlreadyUsedError, ...
      repositories/
        i_sequences_repository.py
        i_establishment_repository.py
    use_cases/
      create_establishment.py
      add_emission_point.py
      edit_emission_point.py     # solo si current == initial
      list_establishments.py
      reserve_next_sequential.py # usado internamente por documents Lambda
    infra/
      sequences_repository.py

  documents/
    handler.py
    schemas.py
    domain/
      entities.py         # Document, InvoiceLine, IvaRate
      commands.py
      errors.py           # DocumentNotFoundError, CertificateNotUploadedError,
                          # DocumentLimitReachedError, ...
      access_key.py       # generate_access_key() → 49 digitos (modulo_11, etc.)
      iva_rates.py        # tabla de tarifas por fecha de emision
      repositories/
        i_documents_repository.py
        i_sequences_port.py      # port para reservar secuencial (implementado por DynamoSequencesAdapter)
    use_cases/
      emit_document.py
      get_document.py
      list_documents.py
      get_ride_url.py
    infra/
      documents_repository.py
      sequences_adapter.py       # implementa i_sequences_port → escribe en tabla sequences

  invoice_processor/
    handler.py             # sqs_handler.py pattern, partial batch failure
    ports.py               # ISriClient, IDocumentStorage, IQueuePublisher
    events.py              # eventos de email (Authorized/BuyerNotification/Rejected/FailedPermanent)
    xml_builder.py         # XML Factura 01 segun especificacion SRI
    signing.py             # XAdES-BES enveloped (cryptography + lxml), RSA-SHA1
    sri_client.py          # SOAP client para recepcion y autorizacion
    sri_error_classifier.py
    ride_builder.py        # PDF RIDE con reportlab
    use_cases/
      sign_document.py
      poll_document.py
    infra/
      certificate_loader.py
      s3_document_storage.py   # S3 put con Object Lock LegalHold
      sqs_event_publisher.py
```

## Firma XAdES-BES

El SRI exige firma electronica XAdES-BES enveloped con el certificado p12 del tenant.
Algoritmo confirmado contra la Ficha Tecnica (Anexo 14): **RSA-SHA1 + digest SHA1 +
C14N 1.0** (`http://www.w3.org/TR/2001/REC-xml-c14n-20010315`) — SHA1 es obligatorio
por el webservice del SRI, no una eleccion de seguridad propia (ver comentarios
`nosec`/`noqa` en `signing.py`). Importante: usar `etree.tostring(el, method="c14n")`
de lxml (C14N 1.0 clasico), **no** `etree.canonicalize()` (es C14N 2.0/RFC 6931, un
algoritmo distinto e incompatible con lo que pide el SRI).

Libreria: `cryptography` + `lxml`. El p12 ya lo sube el tenant via `certificates` Lambda
y esta en Secrets Manager (`tenant.certificate_secret_arn`).

URLs del WebService SOAP segun `tenant.sri_environment`:

```
pruebas:    https://celcer.sri.gob.ec/comprobantes-electronicos-ws/
produccion: https://cel.sri.gob.ec/comprobantes-electronicos-ws/
```

Dos operaciones SOAP, implementadas como envelopes SOAP 1.1 a mano via `urllib3`
(sin WSDL/zeep — el WSDL del SRI ha sido historicamente inestable para fetch en
runtime):
- `RecepcionComprobantesOffline` (`validarComprobante`) — recibe batch de XMLs
  firmados en base64 (max 50, max 500KB)
- `AutorizacionComprobantesOffline` (`autorizacionComprobante`) — consulta estado por
  `claveAccesoComprobante`

**Header `SOAPAction` debe ir vacío (`""`)** — confirmado a mano contra
`celcer.sri.gob.ec` (curl directo, 2026-06-18). El servicio rutea por el nombre de
la operación en el body, no por `SOAPAction`; cualquier valor no vacío (incluido
`"{url}#{operacion}"`, lo que tenía el código original de Sprint 4) responde HTTP 500
con `soap:Fault` *"The given SOAPAction ... does not match an operation"* — este fue
el bug real que dejaba todos los documentos atascados en `PENDING` en la primera
prueba end-to-end. `sri_client.py` también detecta `soap:Fault` explícitamente ahora
(antes se interpretaba silenciosamente como estado de negocio vacío) y lo trata como
error reintentable.

**Declaración XML debe usar comillas dobles** (`<?xml version="1.0" encoding="UTF-8"?>`)
— `lxml` con `xml_declaration=True` emite comillas simples (`version='1.0'`), válidas
por spec XML pero rechazadas en la práctica por el parser del SRI (causaba el mismo
código de error 35 `ARCHIVO NO CUMPLE ESTRUCTURA XML` que `dirEstablecimiento`
faltante — dos bugs distintos con el mismo síntoma). `xml_builder.py` y `signing.py`
ahora construyen la declaración a mano en vez de delegar en lxml. Cubierto por
`test_xsd_compliance.py`, que valida el XML firmado contra el XSD real de Factura
del SRI (`tests/.../sri_xsd/factura_v1.xsd`) — hubiera detectado ambos bugs en CI.

**Digito de `<ambiente>` (Tabla 4, Ficha Tecnica): `1` = Pruebas, `2` = Produccion**
— invertido en el codigo original de Sprints 2/4 (`access_key.py::generate_access_key`
y `xml_builder.py::build_invoice_xml` ambos tenian `"2" if testing else "1"`). Efecto:
todo documento contra `celcer.sri.gob.ec` (ambiente de pruebas) llevaba tanto el tag
`<ambiente>` como el digito 23 de la `claveAcceso` marcados como **Produccion** —
inconsistencia que el SRI rechazaba con el mismo codigo 35 `ARCHIVO NO CUMPLE
ESTRUCTURA XML` que los dos bugs anteriores (tres bugs distintos, mismo sintoma de
superficie). Encontrado el 2026-06-18 cruzando el codigo contra la Tabla 4 de la
Ficha Tecnica oficial provista por el usuario, despues de que los otros dos fixes no
resolvieran el rechazo. Cubierto por `test_access_key.py::test_testing_environment_uses_digit_1`/
`test_production_environment_uses_digit_2` y `test_xml_builder.py` (assertions
sobre `infoTributaria/ambiente`).

Respuesta de recepcion puede ser:
- `RECIBIDA` — SRI acepto el lote; continuar con polling
- `DEVUELTA` — error en el lote; los errores vienen en XML con codigos de error SRI

Respuesta de autorizacion puede ser:
- `AUTORIZADO` — incluye numero de autorizacion y **el XML firmado** (`<comprobante>`,
  eco de lo que el SRI realmente autorizo — es lo que se persiste en S3, no se
  re-genera ni se guarda el firmado de SIGN por separado)
- `EN PROCESO` — en cola del SRI; reintentar con backoff
- Cualquier otro valor (`sri_client.py` lo trata como rechazo) — **pendiente de
  verificar el literal exacto contra el SRI testing real**; la Ficha Tecnica documenta
  `NO AUTORIZADO`, el codigo interno lo representa como `RECHAZADO`. Si la primera
  prueba real muestra un literal distinto, el ajuste es de una linea en
  `sri_client.py::_parse_autorizacion`, sin tocar use cases.

Normalizacion y clasificacion de errores del SRI (critica para no reintentar lo que es
permanente), implementada en `sri_error_mapper.py` con facade legacy
`sri_error_classifier.py`:
- **Permanente** (default para codigos no listados): codigos de error de validacion del
  XML, firma invalida, RUC no registrado, numero de secuencial duplicado. Marcar
  `REJECTED`, no reintentar. Los errores se persisten normalizados con `code`,
  `message`, `user_message`, `category`, `classification`, `raw_message` y
  `additional_info`.
- **Reintentable** (lista corta de codigos conocidos + cualquier error de transporte
  HTTP/timeout/5xx, que ni siquiera llega a tener codigo SRI): marcar `FAILED`,
  retry\_count++, y relanzar excepcion para que SQS reintente (DLQ a los 5 intentos,
  `maxReceiveCount` ya configurado en `QueuesStack`).

## IVA — Tabla De Tarifas

La tarifa correcta se determina por `issued_at` del documento, no por la fecha del sistema.

```python
# documents/domain/iva_rates.py
IVA_RATES = [
    {"from": date(2024, 4,  1), "to": None,              "pct": Decimal("15")},
    {"from": date(2024, 1,  1), "to": date(2024, 3, 31), "pct": Decimal("12")},
]

def iva_rate_for(issued_at: date) -> Decimal:
    for band in IVA_RATES:
        if issued_at >= band["from"] and (band["to"] is None or issued_at <= band["to"]):
            return band["pct"]
    raise ValueError(f"No IVA rate defined for {issued_at}")
```

Si el gobierno cambia la tarifa: agregar una entrada al inicio de `IVA_RATES` con el nuevo
rango. No tocar el resto de la tabla.

## Techo De Descuento Por Linea (Sprint 2c+2d Products, implementado)

Contexto completo de negocio en `context/PRODUCTS.md` (descuento % por producto, Sprint
2a, y campana global de descuento, Sprint 2b). Esta seccion documenta donde vive la
**validacion**, que es codigo de `documents`, no de `products`.

### La regla

Para **toda linea** del documento (con o sin `product_id`), el descuento absoluto que
llega en el request no puede superar:

```text
techo_pct = max(producto.discount_percentage, campana.percentage si campana.active)
techo_monto = (cantidad * precio_unitario) * techo_pct / 100
```

`max`, no suma — si el producto tiene 60% propio y la campana global esta en 50%, el
techo es 60%, no 110%. Cubierto por
`test_ceiling_uses_max_of_product_and_campaign_not_their_sum` en
`tests/unit/lambdas/documents/test_use_cases.py`.

Aplica a lineas manuales (sin `product_id`) tambien — si no hay producto ligado, el unico
input del techo es la campana; sin campana activa y sin producto, el techo es 0% (ver
"Por que aplica a lineas manuales" abajo).

### Por que vive en `documents`, no en `products`

`EmitDocumentUseCase._compute_totals` ya era la unica fuente de verdad de
`unit_price`/`iva_rate` para lineas con `product_id` — el snapshot del producto
**siempre** gana sobre lo que mande el cliente, incluso hoy. El techo de descuento sigue
el mismo principio: se agrego `discount_percentage` a `InvoiceProductSnapshot`
(`documents/domain/repositories/i_product_catalog.py`) y un puerto nuevo,
`IDiscountCampaignPort` (`documents/domain/repositories/i_discount_campaign_port.py`),
con su adapter cross-lambda `DynamoDiscountCampaignCatalog`
(`documents/infra/discount_campaign_catalog.py`) que importa directamente
`lambdas.products.infra.discount_campaign_repository` — mismo patron que ya usaba
`DynamoProductCatalog` para leer la tabla de `products` desde la Lambda `documents`.

### Por que aplica a lineas manuales (no solo a las de catalogo)

Decision explicita: si el techo solo protegiera lineas con `product_id`, alcanzaria con
omitir `product_id` para evadirlo — el caso de uso real que motivo el techo (no sumar
60%+50%) involucra siempre un producto del catalogo, pero dejar las lineas manuales sin
limite habria sido una grieta de seguridad/negocio abierta a proposito. La consecuencia
inevitable: con campana inactiva y sin producto, una linea manual con `discount > 0` es
rechazada por defecto. Por eso el override (siguiente seccion) se implemento **en el
mismo cambio**, no en un sprint separado — lanzar el techo sin el override hubiera roto
el descuento ad-hoc manual que ya funcionaba para todos los tenants, incluso los que
nunca tocaron este feature.

### Override auditado

`EmitDocumentCommand`/`EmitDocumentRequest` aceptan `override_discount_ceiling: bool` +
`override_reason: str | None`. Si `override_discount_ceiling=True`, `override_reason`
es obligatorio (no vacio) — validado en el schema Pydantic **y** en
`EmitDocumentUseCase.execute` (defensa en profundidad, por si algun caller futuro
construye el comando sin pasar por el schema HTTP). Cuando el override se usa, nunca se
salta `discount <= gross` (piso fiscal, no negociable bajo ninguna circunstancia) — solo
se salta el techo `max(producto%, campana%)`.

No hay validacion de rol adicional para el override: emitir documentos ya esta
restringido a `owner|admin|superadmin` a nivel de endpoint (`_emit` en
`documents/handler.py`), asi que cualquier caller capaz de invocar el override ya tiene
el rol necesario. Lo que aporta el override es **trazabilidad explicita**, no una
barrera de permisos nueva: `DynamoDocumentsRepository.save()` escribe un `audit_item`
(`shared/audit/writer.py`) transaccionalmente junto al documento cuando
`override_reason` viene seteado — `entity_type="DOCUMENT"`,
`action="DISCOUNT_CEILING_OVERRIDE"`, `changed_by=user_id`,
`after={"reason", "access_key"}`. `documents` no usaba auditoria antes de este cambio;
se sumo solo para esta accion puntual, no para toda mutacion de `Document`.

### Frontend

`EmitDocumentScreen` consulta la campana activa (`useDiscountCampaign`, mismo hook de
`context/PRODUCTS.md`) y, **solo al seleccionar un producto del catalogo** vía
`ProductPickerModal`, pre-llena el campo de descuento de esa linea con
`resolveSuggestedDiscount()` (`features/documents/form.ts`) — replica en TS de la regla
de arriba, usado solo para UX, el backend es quien valida de verdad. Decision de alcance:
no hay pre-llenado reactivo para lineas manuales (evita sobreescribir un valor que el
usuario ya esta editando); en su lugar se muestra un aviso ("Campaña activa: hasta X% de
descuento por línea") en la seccion de lineas cuando la campana esta activa, para que el
usuario sepa el techo disponible y lo escriba el mismo.

Seccion "Avanzado" en `EmitDocumentScreen`: toggle "Anular techo de descuento" +
`FormField` de motivo (obligatorio si el toggle esta activo), mapeado a
`override_discount_ceiling`/`override_reason` en el payload.

### RIDE (Sprint 2e, implementado)

`ride_builder.py` agrega columna "Subtotal" (precio neto de la linea, post-descuento,
pre-IVA — `line.subtotal`) y la celda "Desc." ahora combina monto absoluto + porcentaje
(`"$5.00 (25.00%)"`, helper `_discount_cell`), calculado en el momento desde
`discount`/`quantity`/`unit_price` ya persistidos — **no** agrega ningun campo nuevo al
XML/XSD del SRI, es puramente de confianza ante el comprador. "P. Unit." se relabeleo a
"P. Unit. orig." para dejar explicito que es el precio antes de aplicar el descuento de
esa linea. Sin discount, la celda muestra "—".

## Consumidor Final — Regla Critica

Para facturas a Consumidor Final **NO se crea ni referencia un Client**. El handler
acepta `client_id=null` con `buyer_id_type="07"` y usa valores fijos:

```
tipoIdentificacionComprador = "07"
identificacionComprador     = "9999999999999"
razonSocialComprador        = "CONSUMIDOR FINAL"
client_id                   = null
```

Desde el 1 de enero de 2026 **no se pueden anular facturas a Consumidor Final** por el
tramite manual de anulacion en linea del SRI. La via real para corregir/reversar su valor
es Nota de Credito (tipo 04, implementada — ver seccion "Nota De Credito (04)"), que **no**
tiene esa restriccion.

## Estados Del Documento

```
PENDING
  ↓ worker SIGN exitoso
PROCESSING
  ↓ POLL: SRI acepto
AUTHORIZED      (terminal exitoso)
  ↓ POLL: SRI rechazo
REJECTED        (terminal, error de negocio permanente)
  ↓ SIGN/POLL: error tecnico reintentable
FAILED          (retry_count < 5 → se reintenta via DLQ)
  ↓ retry_count >= 5
FAILED_PERMANENT  (terminal, requiere intervencion manual)
```

Clasificacion de errores:
- **Reintentable**: timeout SRI, HTTP 5xx SRI, error de red transitorio.
- **Permanente**: XML invalido, RUC no registrado, secuencial duplicado, firma invalida.

El worker DEBE clasificar el error antes de decidir reintentar o marcar permanente.
La clasificacion vive en `sri_client.py` usando los codigos de error del SRI.

## API Contract

Todos los endpoints requieren JWT (owner o admin del tenant). `tenant_id` viene del JWT.

### Establishments (dentro de lambda `sequences`)

| Metodo | Ruta | Descripcion |
| --- | --- | --- |
| GET | `/tenants/{id}/establishments` | lista establecimientos + puntos de emision |
| POST | `/tenants/{id}/establishments` | crear establecimiento |
| POST | `/tenants/{id}/establishments/{code}/emission-points` | agregar punto de emision |
| PATCH | `/tenants/{id}/establishments/{code}/emission-points/{ep}` | editar (solo si sin uso aun) |

Solo el owner puede crear/editar establecimientos. Los admin/viewer pueden leer.
El superadmin puede hacer todo.

### Documents

| Metodo | Ruta | Descripcion |
| --- | --- | --- |
| POST | `/documents` | emitir Factura (`doc_type:"01"`) o Nota de Credito (`doc_type:"04"`) — mismo endpoint, body distinto por tipo (`EmitDocumentRequest`/`EmitCreditNoteRequest`), 202 Accepted |
| GET | `/documents` | lista paginada con filtros (status, doc\_type, date\_from, date\_to, serie, q) |
| GET | `/documents/{id}` | detalle + estado actual |
| GET | `/documents/{id}/ride` | pre-signed URL S3 al RIDE (solo si AUTHORIZED) |
| GET | `/documents/{id}/xml` | pre-signed URL S3 al XML firmado (solo si AUTHORIZED) |
| POST | `/documents/{id}/annul` | legacy — marca local sin SRI, deprecado (ver "Anulacion De Documentos") |

### Sequences (consulta interna — no HTTP publico)

Los contadores de secuencial no se exponen via HTTP. Solo el Lambda `documents` los
usa via `DynamoSequencesAdapter` con acceso directo a la tabla `sequences`.

## Errores De Dominio

```python
# sequences/domain/errors.py
SequenceExhaustedError     # contador llego a 999999999
SequenceAlreadyUsedError   # intento editar initial_sequential despues del primer uso
EstablishmentNotFoundError
EmissionPointCode099Reserved # intento crear manualmente el punto 099

# documents/domain/errors.py
DocumentNotFoundError
CertificateNotUploadedError  # tenant sin certificado p12 intenta emitir
DocumentLimitReachedError    # plan.document_limit mensual superado
InvalidIssuedDateError       # issued_at en el futuro

# invoice_processor reusa shared.errors.ExternalServiceError (no define excepciones
# propias) tanto para errores de transporte SOAP como para el caso "SRI devolvio un
# error reintentable" — en ambos casos el efecto deseado es el mismo: que sqs_handler
# marque el mensaje como fallido y SQS lo reintente.
```

## Infra CDK — Componentes Nuevos

Stacks a crear o modificar:

| Stack | Cambio |
| --- | --- |
| `StorageStack` (nuevo) | S3 bucket documents (Object Lock + lifecycle) |
| `DatabaseStack` (existente) | Tablas `sequences`, `documents`, `batch_jobs` |
| `QueuesStack` (existente) | Colas `invoice-sign` + `invoice-poll` + sus DLQs + alarmas |
| `ApiStack` (existente) | Lambdas `sequences`, `documents`, `invoice_processor` + ESMs |

## Frontend — Estructura (Sprint 5, implementado)

```
frontend/features/documents/
  api.ts                 # GET/POST /documents (emit + emitCreditNote), GET /documents/{id}, GET /documents/{id}/xml|ride
  schemas.ts             # Zod: documento, pagina paginada, input de emision (factura + nota de credito), form values
  types.ts               # tipos derivados + DocumentListFilters (incluye doc_type)
  constants.ts           # status labels/badge variant, iva rates, buyer_id_types, payment methods, DOC_TYPE_LABELS
  form.ts                # defaults, formValuesToEmitDocumentInput, computeLineTotals (preview) — solo Factura
  creditNoteForm.ts       # defaults/conversion/preview de totales para Nota de Credito (escalado proporcional, espeja backend)
  filters.ts             # filtros de listado; `q` busca numero SRI, cedula/RUC, access key o nombre
  utils.ts                # getCreditNoteBlockReason (elegibilidad: doc_type 01 + AUTHORIZED)
  hooks/
    useDocuments.ts        # useCursorPagedList con paginacion 10/25/50
    useDocument.ts         # useFetch + auto-poll cada 5s mientras PENDING/PROCESSING
  components/
    DocumentStatusBadge.tsx
    DocumentListItem.tsx     # RowActionsMenu con descargas XML/RIDE y "Anular factura" (navega a credit-note locked)
    DocumentsFilters.tsx
    DocumentLineRow.tsx      # fila compacta de una linea por producto (lista escaneable)
    DocumentLineEditModal.tsx # modal de detalle (cantidad/descuento/IVA/codigo/descripcion)
    IvaRatePicker.tsx       # SegmentedControl de 4 tarifas
    BuyerSection.tsx        # 2 modos: Consumidor Final / Cliente existente — sin "Manual" (solo Factura)
    BuyerReadOnlySection.tsx # comprador solo-lectura para Nota de Credito (siempre viene de la factura padre)
    ClientPickerModal.tsx   # busca clientsApi.list({q}) + creacion rapida (igual patron que ProductPickerModal)
    InvoicePickerModal.tsx  # busca documentsApi.list({status:AUTHORIZED, doc_type:'01', q}) — sin creacion rapida
  screens/
    DocumentsListScreen.tsx
    EmitDocumentScreen.tsx
    EmitCreditNoteScreen.tsx # pantalla unica Nota de Credito — locked (Anular) o editable, ver seccion de dominio
    DocumentDetailScreen.tsx

frontend/features/sequences/
  api.ts                  # /tenants/{tenantId}/establishments...
  schemas.ts
  types.ts
  hooks/
    useEstablishments.ts   # useFetch (lista completa, sin paginacion)
  components/
    EstablishmentCard.tsx  # card con sus puntos de emision + alta/edicion inline
  screens/
    EstablishmentsScreen.tsx  # pantalla unica: alta de establecimiento + EstablishmentCard*
```

Decision tomada en Sprint 5 (no en el diseño original): no hay `useEmitDocument.ts`
separado — `EmitDocumentScreen` usa `useFormSubmit` inline, igual que
`NewClientScreen` (patron ya establecido en el repo para creacion). El selector de
comprador integra busqueda de clientes existentes (`ClientPickerModal`), no solo
entrada manual — decision de producto tomada explicitamente en este sprint.

**Rediseño de UX de emision (post-MVP):** `BuyerSection` elimino el modo "Manual" —
los campos de identificacion/nombre/email del comprador quedan siempre disabled,
poblados unicamente al elegir un cliente real via `ClientPickerModal` (que ahora tiene
creacion rapida inline, igual patron que `ProductPickerModal`). Nunca se permite
facturar a una identidad que no quede guardada como `Client`.

La creacion rapida de `ClientPickerModal` pide tipo/numero de identificacion, tipo de
persona y razon social (obligatorios), mas **correo (obligatorio)**, telefono y
direccion (ambos opcionales) — el correo es obligatorio aqui porque este cliente se
factura de inmediato; no aplica a Consumidor Final, que nunca abre este modal (usa el
placeholder fijo `9999999999999`, sin cambios). `ClientForm.tsx` (alta/edicion completa
de clientes fuera del flujo de facturacion) sigue con email/telefono/direccion
opcionales — la obligatoriedad es especifica de "el cliente que se factura", no una
regla nueva del dominio `Client` en general.

El selector de establecimiento/punto de emision en `EmitDocumentScreen` solo usa
`SegmentedControl` cuando hay mas de una opcion real entre las que elegir. Con un solo
establecimiento o un solo punto (caso comun: tenant chico con su unico establecimiento +
punto 099 de pruebas) se renderiza como `LockedInfoRow` (icono+label+valor+candado, mismo
lenguaje visual que `LockedIssuedAt`/Fecha de emision) en vez de un `SegmentedControl` de
una sola opcion, que se veia como un boton vacio sin proposito y dejaba espacio en blanco
desparejo frente a la card de Fecha de emision. Generalizable: cualquier futuro
`SegmentedControl` que pueda quedar con 0-1 opciones reales deberia evaluar el mismo
tratamiento en vez de renderizar el control igual.

La lista de productos (`EmitDocumentScreen`) es ahora `DocumentLineRow` (una fila por
linea + eliminar) en vez de un card siempre expandido por linea — pensado para listas
largas (ej. flujos con lector de codigo de barras a futuro) donde un card por linea
sobrecargaria la pantalla. Sigue el mismo patron responsive de toda fila de listado
(`useIsDesktopLayout` + `ListCell`, ver `ProductListItem`/`ClientListItem`): en desktop
se ve como fila de columnas (Producto/codigo, Cantidad, Precio unit., Descuento, Sin IVA,
Con IVA) en vez de una sola linea de texto comprimida, aprovechando el ancho disponible;
en mobile colapsa a nombre + meta compacta + `Sin IVA $X` / total con IVA en una fila de
totales. El descuento se muestra como `Badge variant="warning"` con `-$monto (pct%)` —
mismo formato y misma formula (`discount / (quantity*unit_price) * 100`) que
`_discount_cell` en `ride_builder.py` (Sprint 2e), para que el front no invente un
numero distinto al que ya se le muestra al comprador en el RIDE. El boton "Agregar
producto" abre `ProductPickerModal` (busqueda + creacion rapida); si el producto
elegido ya esta en la lista, suma +1 a su cantidad en vez de duplicar la linea. El
detalle de cada linea (cantidad/descuento/IVA/codigo/descripcion) se edita en
`DocumentLineEditModal`, no inline — toda fila nueva nace desde `ProductPickerModal`,
nunca como una linea en blanco para tipear a mano; por eso `defaultEmitDocumentFormValues`
arranca con `lines: []`. Se evaluo agregar tambien un campo de escaneo siempre visible
con lookup automatico por SKU exacto, pero se descarto por UX confusa (mezclaba
"buscar" y "agregar" en un mismo input sin flujo claro) — si se retoma, debe ser un
input separado y explicito, no un atajo silencioso sobre el boton existente.

Decision posterior de UX: el listado de documentos expone una busqueda general `q`
reactiva (minimo 3 caracteres) que matchea numero SRI con o sin guiones
(`001-001-000000001` / `001001000000001`), secuencial, serie, clave de acceso,
cedula/RUC del comprador y nombre del comprador. `serie` queda como filtro tecnico
compatible de API.

Rutas Expo Router:

```
(app)/(tenant)/documents/         → DocumentsListScreen
(app)/(tenant)/documents/emit     → EmitDocumentScreen
(app)/(tenant)/documents/[id]     → DocumentDetailScreen
(app)/(tenant)/settings/estab     → EstablishmentsScreen
```

Nav (`features/navigation/items.ts`): "Documentos" y "Establecimientos" agregados a
`tenantNavigation`.

## Prerequisitos Para Empezar

| Prerequisito | Estado |
| --- | --- |
| Certificados p12 — tenants pueden subirlos | Listo (`certificates` Lambda) |
| `plans.document_limit` existe | Listo |
| `plans.dedicated_queue` existe | Listo |
| `tenants.sri_environment` existe | Listo (nace en `testing`) |
| `tenants.address` existe | Listo (`dirMatriz` en XML) |
| `tenants.accounting_required` existe | Listo (`obligadoContabilidad` en XML) |
| Tabla `sequences` en DynamoDB | Sprint 1 |
| Tabla `documents` en DynamoDB | Sprint 1 |
| S3 bucket con Object Lock | Sprint 1 |
| Colas SQS invoice-sign + invoice-poll | Sprint 1 |
| Lambda `invoice_processor` (SIGN + POLL) | Sprint 4 |
| `IDocumentsRepository.update_status` (transicion condicional de estado) | Sprint 4 |
| Eventos de email `DocumentAuthorizedEvent`/`RejectedEvent`/`FailedPermanentEvent` | Sprint 4 |
| Notificacion al comprador con XML autorizado + RIDE adjuntos | Sprint 6 |

## Deuda Tecnica Anticipada

| Deuda | Impacto |
| --- | --- |
| Tabla IVA hardcodeada en codigo | Si el gobierno cambia la tarifa hay que hacer deploy. Evaluar tabla DynamoDB con rangos de fecha cuando el gobierno sea menos predecible. |
| Mapeo de errores SRI incompleto | El SRI Ecuador tiene ~50 codigos de error. El mapeo inicial cubre los mas comunes y el codigo 69 observado en testing. Afinar con datos reales de produccion. |
| Colas enterprise dedicadas sin cleanup automatico | Si un tenant enterprise es dado de baja, su cola y ESM quedan huerfanos. Necesita un proceso de deprovision. |
| Worker SIGN sin agrupacion de tenants en cola compartida | Para clientes pequenos, cada documento = 1 llamada SOAP al SRI (no hay batching entre distintos RUCs). Aceptable hasta ~50,000 docs/dia en la cola compartida. |
| Scans de batch\_jobs para listado | Igual que tenants/clients: aceptable para volumen bajo. |
| Literal de estado "rechazado" en autorizacion SOAP sin verificar contra SRI real | `sri_client.py` asume que todo lo que no es `AUTORIZADO`/`EN PROCESO` es rechazo; falta confirmar el literal exacto (`NO AUTORIZADO` segun Ficha Tecnica) contra el ambiente de pruebas real del SRI. Ajuste aislado a una funcion si difiere. |
| Nota de Credito solo puede referenciar Factura (01), no otra NC | Encadenar notas de credito sobre notas de credito no esta soportado en v1 — fuera de alcance hasta que se necesite (decision deliberada, no limitacion tecnica). |
| Secuencial inicial de Nota de Credito no configurable | El contador "04" arranca en 1 via bootstrap perezoso (ver seccion "Nota De Credito"). Un tenant que ya emitia NC por otro sistema antes de Wali no tiene forma de fijar un secuencial inicial distinto — mismo espiritu que la limitacion ya documentada para Factura, pero sin la UI equivalente para NC. |
| Estructura de `<infoNotaCredito>` sin XSD real para validar | El repo solo tiene `sri_xsd/factura_v1.xsd`. `build_credit_note_xml` se implemento con la Ficha Tecnica documentada (sin `<pagos>`, version "1.1.0") pero sin un test de compliance XSD equivalente al de Factura — validar contra el ambiente de pruebas real del SRI antes de produccion. |
| `Establecimiento` sin direccion propia | `dirEstablecimiento` (obligatorio en XSD) reusa `tenant.address` para todos los establecimientos del tenant. Agregar `address` a `Establecimiento` si se necesita una direccion real por sucursal. |
| RIDE sin codigo de barras real ni logo del tenant | MVP genera PDF con todos los campos obligatorios en texto via reportlab. Agregar barcode Code128/logo es trabajo de UI, no de cumplimiento legal — evaluar si un cliente lo pide. |
| `EstablishmentsScreen` con forms inline via `useState` plano (no react-hook-form) | Los mini-forms de alta/edicion de punto de emision son simples (2-3 campos) y no justifican el overhead de react-hook-form+zod. Si crecen en complejidad, migrar al patron `*Form.tsx` + Controller. |
| Emails de documento al emisor sin adjuntar PDF | `DocumentAuthorizedEvent` etc. notifican al emisor sin adjuntos. El emisor descarga el RIDE desde `GET /documents/{id}/ride`. El comprador si recibe XML autorizado + RIDE adjuntos via `DocumentBuyerNotificationRequestedEvent`. |
| `invoice_processor` SIGN/POLL sin concurrencia reservada diferenciada | Cuenta AWS en `sa-east-1` con limite de Lambda en 10 ejecuciones concurrentes totales (default no aumentado). Pedir quota increase a AWS y reintroducir `reserved_concurrent_executions=30/20` en `api_stack.py` cuando se apruebe. |
