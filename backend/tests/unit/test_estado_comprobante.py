import pytest
from app.domain.entities.comprobante import Comprobante
from app.domain.enums.estado_comprobante import EstadoComprobante
from app.domain.enums.tipo_comprobante import TipoComprobante
from app.shared.exceptions import DomainError
import uuid


def make_comprobante(**kwargs) -> Comprobante:
    defaults = dict(
        tenant_id=uuid.uuid4(),
        tipo=TipoComprobante.FACTURA,
        establecimiento="001",
        punto_emision="001",
        datos={"total": 100.0},
    )
    return Comprobante(**{**defaults, **kwargs})


def test_valid_transition():
    c = make_comprobante()
    c.transition_to(EstadoComprobante.PENDING_VALIDATION)
    assert c.estado == EstadoComprobante.PENDING_VALIDATION


def test_invalid_transition_raises():
    c = make_comprobante()
    with pytest.raises(DomainError) as exc:
        c.transition_to(EstadoComprobante.AUTHORIZED)
    assert exc.value.code == "INVALID_STATE_TRANSITION"


def test_increment_retry():
    c = make_comprobante()
    c.increment_retry()
    c.increment_retry()
    assert c.retry_count == 2


def test_mark_failed():
    c = make_comprobante()
    c.mark_failed("Error de firma")
    assert c.estado == EstadoComprobante.FAILED
    assert c.error_detalle == "Error de firma"
