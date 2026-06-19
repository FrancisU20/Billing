from __future__ import annotations

"""
Base domain entity hierarchy.

GlobalEntity       — root system entities with no owner (Tenant, Plan, etc.)
TenantScopedEntity — entities that belong to a tenant (Client, Invoice, etc.)

Inheritance tree:
    GlobalEntity
        └── TenantScopedEntity

Rule: every repository that uses BaseRepository must receive a TenantScopedEntity.
      GlobalEntity repositories (e.g. TenantRepository) are standalone.
"""

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

from shared.dates import now_utc


def _now() -> datetime:
    return now_utc()


def _uuid() -> str:
    return str(uuid4())


@dataclass
class GlobalEntity:
    """Base for global entities — no tenant isolation."""

    id: str = field(default_factory=_uuid)
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    created_by: str = ""
    updated_by: str = ""
    version: int = 1
    deleted: bool = False
    deleted_at: datetime | None = None
    deleted_by: str | None = None

    def touch(self, updated_by: str) -> None:
        """Record a modification — increments version and timestamp."""
        self.updated_at = _now()
        self.updated_by = updated_by
        self.version += 1

    def soft_delete(self, deleted_by: str) -> None:
        """Mark as deleted without physically removing the record."""
        self.deleted = True
        self.deleted_at = _now()
        self.deleted_by = deleted_by
        self.touch(deleted_by)


@dataclass
class TenantScopedEntity(GlobalEntity):
    """Base for entities that belong to a specific tenant."""

    tenant_id: str = ""

    def __post_init__(self) -> None:
        if not self.tenant_id:
            raise ValueError(f"{self.__class__.__name__}.tenant_id is required")
