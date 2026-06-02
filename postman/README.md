# Postman — CodeLabs Billing Cloud

## Cómo importar

1. Abrir Postman → **Import**
2. Importar `CodeLabsBillingCloud.postman_collection.json`
3. Importar el environment de `environments/`:
   - `local.postman_environment.json` para desarrollo local
   - `dev.postman_environment.json` para el ambiente dev en AWS

## Variables de environment

| Variable | Descripción | Llenar manualmente |
|---|---|---|
| `base_url` | URL base de la API | Ya viene configurada |
| `token` | JWT de Cognito | Sí — copiar desde el login |
| `tenant_id` | UUID del tenant activo | Se autocompleta al crear un tenant |
| `cert_id` | UUID del certificado | Se autocompleta al solicitar upload-url |
| `s3_upload_url` | Presigned URL de S3 | Se autocompleta al solicitar upload-url |

## Cómo obtener el token (local)

Con la API corriendo localmente (`make backend-dev`), el Lambda Authorizer no se ejecuta.
El `TenantContext` acepta el header `X-Tenant-Id` para desarrollo local.

Dejar el token vacío y agregar el header:
```
X-Tenant-Id: uuid-del-tenant
```

## Estructura de la colección

```
CodeLabs Billing Cloud
├── System
│   └── GET /health
├── Auth
│   └── GET /auth/me
├── Tenants (superadmin)
│   ├── GET  /tenants
│   ├── POST /tenants              ← guarda tenant_id en env automáticamente
│   ├── GET  /tenants/:id
│   └── PATCH /tenants/:id
└── Certificates
    ├── GET  /tenants/:id/certificates
    ├── POST /tenants/:id/certificates/upload-url  ← guarda cert_id + s3_upload_url
    ├── PUT  {{s3_upload_url}}      ← subir .p12 directo a S3
    └── POST /tenants/:id/certificates/confirm
```

## Convención de nombres para nuevos endpoints

Al agregar endpoints de nuevas fases, usar el formato:
```
MÉTODO /ruta/completa — descripción breve
```
Ejemplo: `POST /comprobantes — emitir factura individual`

Agrupar por recurso en carpetas. Incluir siempre al menos un ejemplo de respuesta exitosa.
