from abc import ABC, abstractmethod
from uuid import UUID
from app.domain.entities.tenant import Tenant


class TenantRepository(ABC):

    @abstractmethod
    async def get_by_id(self, tenant_id: UUID) -> Tenant | None: ...

    @abstractmethod
    async def get_by_ruc(self, ruc: str) -> Tenant | None: ...

    @abstractmethod
    async def save(self, tenant: Tenant) -> Tenant: ...

    @abstractmethod
    async def list_all(self, offset: int = 0, limit: int = 50) -> list[Tenant]: ...
