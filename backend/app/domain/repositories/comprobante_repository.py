from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.entities.comprobante import Comprobante
from app.domain.enums.estado_comprobante import EstadoComprobante


class ComprobanteRepository(ABC):

    @abstractmethod
    async def get_by_id(self, comprobante_id: UUID, tenant_id: UUID) -> Comprobante | None: ...

    @abstractmethod
    async def get_by_idempotency_key(self, tenant_id: UUID, key: str) -> Comprobante | None: ...

    @abstractmethod
    async def get_by_clave_acceso(self, clave_acceso: str) -> Comprobante | None: ...

    @abstractmethod
    async def save(self, comprobante: Comprobante) -> Comprobante: ...

    @abstractmethod
    async def update_estado(
        self, comprobante_id: UUID, nuevo_estado: EstadoComprobante, metadata: dict | None = None,
    ) -> None: ...

    @abstractmethod
    async def list_retry_pending(self, tenant_id: UUID | None = None, limit: int = 100) -> list[Comprobante]: ...
