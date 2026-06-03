from fastapi import APIRouter

from app.api.v1.routes import (
    api_keys,
    auth,
    certificates,
    comprobantes,
    config,
    establecimientos,
    lotes,
    reportes,
    tenants,
    usuarios,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(config.router, prefix="/config", tags=["config"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
api_router.include_router(
    certificates.router,
    prefix="/tenants/{tenant_id}/certificates",
    tags=["certificates"],
)
api_router.include_router(establecimientos.router, prefix="/tenants", tags=["establecimientos"])
api_router.include_router(usuarios.router, prefix="/tenants", tags=["usuarios"])
api_router.include_router(comprobantes.router, prefix="/comprobantes", tags=["comprobantes"])
api_router.include_router(lotes.router, prefix="/lotes", tags=["lotes"])
api_router.include_router(reportes.router, prefix="/reportes", tags=["reportes"])
api_router.include_router(api_keys.router, prefix="/api-keys", tags=["api-keys"])
