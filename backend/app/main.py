from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.shared.config import get_settings
from app.shared.logging import configure_logging

configure_logging()
settings = get_settings()

if settings.env == "prod" and settings.cors_origins == ["*"]:
    raise ValueError(
        "cors_origins no puede ser ['*'] en producción. "
        "Configura CORS_ORIGINS con el dominio específico del frontend."
    )

api_app = FastAPI(
    title="CodeLabs Billing Cloud API",
    version="0.1.0",
    docs_url="/docs" if settings.env != "prod" else None,
    redoc_url="/redoc" if settings.env != "prod" else None,
)

if settings.is_local:
    from app.shared.middleware.local_auth_middleware import LocalAuthMiddleware
    api_app.add_middleware(LocalAuthMiddleware)

api_app.include_router(api_router, prefix="/api/v1")


@api_app.get("/health")
def health():
    return {"status": "ok", "env": settings.env}


app = CORSMiddleware(
    api_app,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Content-Type", "Authorization", "X-Api-Key", "X-Idempotency-Key"],
)
