"""
Factories de repositorios para inyección de dependencias en FastAPI.
Los routes dependen de las interfaces de dominio, no de las implementaciones concretas.
"""
from typing import Annotated

from fastapi import Depends

from app.domain.repositories.comprobante_repository import ComprobanteRepository
from app.domain.repositories.tenant_repository import TenantRepository
from app.infrastructure.database.repositories.certificate_repository import CertificateRepository
from app.infrastructure.database.repositories.comprobante_repository import SqlAlchemyComprobanteRepository
from app.infrastructure.database.repositories.establecimiento_repository import (
    EstablecimientoRepository,
    PuntoEmisionRepository,
    SecuencialRepository,
)
from app.infrastructure.database.repositories.tenant_repository import SqlAlchemyTenantRepository
from app.infrastructure.database.repositories.user_repository import UserRepository
from app.shared.dependencies import DbSession


def _tenant_repo(db: DbSession) -> TenantRepository:
    return SqlAlchemyTenantRepository(db)


def _comprobante_repo(db: DbSession) -> ComprobanteRepository:
    return SqlAlchemyComprobanteRepository(db)


def _establecimiento_repo(db: DbSession) -> EstablecimientoRepository:
    return EstablecimientoRepository(db)


def _punto_emision_repo(db: DbSession) -> PuntoEmisionRepository:
    return PuntoEmisionRepository(db)


def _secuencial_repo(db: DbSession) -> SecuencialRepository:
    return SecuencialRepository(db)


def _certificate_repo(db: DbSession) -> CertificateRepository:
    return CertificateRepository(db)


TenantRepo = Annotated[TenantRepository, Depends(_tenant_repo)]
ComprobanteRepo = Annotated[ComprobanteRepository, Depends(_comprobante_repo)]
EstablecimientoRepo = Annotated[EstablecimientoRepository, Depends(_establecimiento_repo)]
PuntoEmisionRepo = Annotated[PuntoEmisionRepository, Depends(_punto_emision_repo)]
SecuencialRepo = Annotated[SecuencialRepository, Depends(_secuencial_repo)]
def _user_repo(db: DbSession) -> UserRepository:
    return UserRepository(db)


CertificateRepo = Annotated[CertificateRepository, Depends(_certificate_repo)]
UserRepo = Annotated[UserRepository, Depends(_user_repo)]
