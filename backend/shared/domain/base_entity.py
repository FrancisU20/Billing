"""
Jerarquía de entidades base del dominio.

GlobalEntity      — entidades raíz del sistema sin dueño (Tenant, Plan, etc.)
TenantScopedEntity — entidades que pertenecen a un tenant (Client, Invoice, etc.)

Árbol de herencia:
    GlobalEntity
        └── TenantScopedEntity

Regla: todo repositorio que use BaseRepository debe recibir TenantScopedEntity.
       Los repositorios de GlobalEntity (ej. TenantRepository) son standalone.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid4())


@dataclass
class GlobalEntity:
    """Base para entidades globales — sin aislamiento de tenant."""
    id:         str      = field(default_factory=_uuid)
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    created_by: str      = ""
    updated_by: str      = ""
    version:    int      = 1
    deleted:    bool     = False
    deleted_at: datetime | None = None
    deleted_by: str | None      = None

    def touch(self, updated_by: str) -> None:
        """Registra una modificación — incrementa versión y timestamp."""
        self.updated_at = _now()
        self.updated_by = updated_by
        self.version   += 1

    def soft_delete(self, deleted_by: str) -> None:
        """Marca como eliminado sin borrar el registro físico."""
        self.deleted    = True
        self.deleted_at = _now()
        self.deleted_by = deleted_by
        self.touch(deleted_by)


@dataclass
class TenantScopedEntity(GlobalEntity):
    """Base para entidades que pertenecen a un tenant específico."""
    tenant_id: str = ""

    def __post_init__(self) -> None:
        if not self.tenant_id:
            raise ValueError(
                f"{self.__class__.__name__}.tenant_id es requerido"
            )
