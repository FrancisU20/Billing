# CodeLabs Billing Cloud

SaaS ecuatoriano de facturación electrónica multitenant, serverless y enterprise.

## Stack

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12 · FastAPI · SQLAlchemy 2.x · Alembic |
| Frontend web | Vite · React · TypeScript · Tailwind |
| Frontend mobile | Expo React Native (fase posterior) |
| Infra | AWS CDK (Python) · sa-east-1 |
| Auth | Amazon Cognito |
| DB | Aurora PostgreSQL Serverless v2 |
| Queue | Amazon SQS |
| Storage | Amazon S3 |

## Estructura

```
.
├── backend/        Python FastAPI — clean architecture
├── frontend/
│   ├── web/        Vite React SPA
│   ├── mobile/     Expo React Native (base)
│   └── shared/     Contratos, tipos y schemas compartidos
├── infra/          AWS CDK stacks
├── docs/           Arquitectura y runbooks
└── scripts/        Setup y utilidades
```

## Frontend web

`frontend/web` es una SPA operativa construida con Vite, React, TypeScript, Tailwind, React Router y TanStack Query.

La arquitectura actual separa:

- `src/components/ui/`: sistema reusable de UI (`Button`, `Input`, `Select`, `Card`, `Badge`, `Alert`, `Table`, `Tabs`, `Toast`, `LoadingState`, etc.).
- `src/layouts/`: shells de aplicación. `AppShell` centraliza navegación lateral, marca, logout y contenedor principal.
- `src/lib/`: utilidades transversales (`api-errors`, `format`, `status-styles`, `validation`, `utils`).
- `src/pages/`: pantallas por dominio.
- `src/components/{certificates,comprobantes,configuracion}`: componentes de dominio que consumen UI base.

### Sistema visual

El diseño usa una línea premium SaaS con marca negro + índigo:

- Los colores globales viven en `frontend/web/src/index.css`.
- Los tokens Tailwind viven en `frontend/web/tailwind.config.ts`.
- No se deben hardcodear colores tipo `bg-green-*`, `text-red-*`, etc. en pantallas. Usar tokens semánticos (`success`, `warning`, `danger`, `info`, `brand`) y helpers de `src/lib/status-styles.ts`.
- Inputs, selects y botones deben salir de `src/components/ui`, no de elementos HTML directos en páginas.
- Mensajes de éxito/error deben usar `ToastProvider` + `useToast` o `Alert` según el caso.

### Shared frontend

`frontend/shared` es un paquete TypeScript puro de contratos. Contiene tipos y schemas `zod` alineados con los responses/requests reales del backend:

- `contracts/tenant`
- `contracts/comprobante`
- `contracts/factura`
- `contracts/sri`
- `contracts/certificate`
- `contracts/establecimiento`
- `contracts/api`

No contiene cliente HTTP ni lógica de plataforma. El cliente Axios vive en `frontend/web/src/lib/api-client.ts`.

### Validación

```bash
cd frontend/shared && npm run typecheck
cd frontend/web && npm run build
```

## Setup local

```bash
make setup
```

## Deploy dev

```bash
make deploy-dev
```

## Documentación

- [Arquitectura](docs/architecture.md)
- [Integración SRI](docs/sri-integration.md)
