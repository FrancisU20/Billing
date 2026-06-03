from dataclasses import dataclass, field
from uuid import UUID, uuid4


@dataclass
class Receptor:
    tipo_identificacion: str  # 04=RUC, 05=cedula, 06=pasaporte, 07=consumidor_final, 08=id_exterior
    identificacion: str
    razon_social: str
    id: UUID = field(default_factory=uuid4)
    email: str | None = None
    telefono: str | None = None
    direccion: str | None = None
    tenant_id: UUID | None = None

    def is_consumidor_final(self) -> bool:
        return self.tipo_identificacion == "07"

    def display_name(self) -> str:
        return self.razon_social or self.identificacion
