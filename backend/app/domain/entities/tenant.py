from dataclasses import dataclass, field
from uuid import UUID, uuid4
from datetime import datetime, timezone
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
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def can_emit(self) -> bool:
        return EstadoTenant(self.estado).can_emit

    def is_production(self) -> bool:
        return self.ambiente_sri == "PRODUCCION"
