# CodeLabs Billing Cloud

SaaS ecuatoriano de facturación electrónica multitenant, serverless y enterprise.

## Stack

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12 · FastAPI · SQLAlchemy 2.x · Alembic |
| Frontend web | Next.js 15 · TypeScript · Tailwind · shadcn/ui |
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
│   ├── web/        Next.js 15 App Router
│   ├── mobile/     Expo React Native (base)
│   └── shared/     Tipos y cliente API compartido
├── infra/          AWS CDK stacks
├── docs/           Arquitectura y runbooks
└── scripts/        Setup y utilidades
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
