from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.enums.estado_tenant import EstadoTenant


@dataclass
class Tenant:
    ruc: str
    razon_social: str
    id: UUID = field(default_factory=uuid4)
    nombre_comercial: str | None = None
    estado: EstadoTenant = EstadoTenant.TRIAL
    ambiente_sri: str = "PRUEBAS"  # PRUEBAS | PRODUCCION
    plan_id: UUID | None = None
    comprobantes_mes_actual: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def can_emit(self) -> bool:
        return EstadoTenant(self.estado).can_emit

    def is_production(self) -> bool:
        return self.ambiente_sri == "PRODUCCION"
