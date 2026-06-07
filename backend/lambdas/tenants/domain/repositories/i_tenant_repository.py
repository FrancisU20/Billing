"""
Interfaz del repositorio de Tenants.

El dominio define el contrato. La infraestructura lo implementa.
Los use cases dependen de esta interfaz — nunca de DynamoDB directamente.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from lambdas.tenants.domain.tenant import Tenant


class ITenantRepository(ABC):

    @abstractmethod
    def get_by_id(self, tenant_id: str) -> Tenant:
        """Lanza TenantNotFoundError si no existe o está soft-deleted."""

    @abstractmethod
    def get_by_ruc(self, ruc: str) -> Tenant | None:
        """Retorna None si no existe. Incluye soft-deleted: el RUC no se recicla."""

    @abstractmethod
    def save(self, tenant: Tenant, user_id: str) -> None:
        """Crea o actualiza. Lanza OptimisticLockError si hubo modificación concurrente."""

    @abstractmethod
    def list(
        self,
        limit:      int,
        next_token: str | None,
        estado:     str | None = None,
    ) -> tuple[list[Tenant], str | None]:
        """Retorna (items, next_token). next_token=None si no hay más páginas."""

    @abstractmethod
    def delete(self, tenant_id: str, deleted_by: str) -> None:
        """Soft delete. Lanza TenantNotFoundError si no existe."""
