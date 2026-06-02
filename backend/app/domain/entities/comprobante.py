from dataclasses import dataclass, field
from uuid import UUID, uuid4
from datetime import datetime
from app.domain.enums.estado_comprobante import EstadoComprobante
from app.domain.enums.tipo_comprobante import TipoComprobante
from app.shared.exceptions import DomainError


@dataclass
class Comprobante:
    tenant_id: UUID
    tipo: TipoComprobante
    establecimiento: str
    punto_emision: str
    datos: dict
    id: UUID = field(default_factory=uuid4)
    clave_acceso: str | None = None
    secuencial: str | None = None
    estado: EstadoComprobante = EstadoComprobante.DRAFT
    idempotency_key: str | None = None
    external_reference: str | None = None
    numero_autorizacion: str | None = None
    fecha_autorizacion: datetime | None = None
    s3_key_xml: str | None = None
    s3_key_xml_firmado: str | None = None
    s3_key_xml_autorizado: str | None = None
    s3_key_pdf: str | None = None
    lote_id: UUID | None = None
    retry_count: int = 0
    error_detalle: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def transition_to(self, nuevo_estado: EstadoComprobante) -> None:
        valid = EstadoComprobante.VALID_TRANSITIONS.get(self.estado, set())
        if nuevo_estado not in valid:
            raise DomainError(
                f"Transición inválida: {self.estado} → {nuevo_estado}",
                code="INVALID_STATE_TRANSITION",
            )
        self.estado = nuevo_estado
        self.updated_at = datetime.utcnow()

    def increment_retry(self) -> None:
        self.retry_count += 1
        self.updated_at = datetime.utcnow()

    def mark_failed(self, reason: str) -> None:
        self.error_detalle = reason
        self.estado = EstadoComprobante.FAILED
        self.updated_at = datetime.utcnow()
