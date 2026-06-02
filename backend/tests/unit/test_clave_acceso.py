from datetime import date
from app.domain.value_objects.clave_acceso import ClaveAcceso


def test_clave_acceso_length():
    clave = ClaveAcceso.generate(
        fecha_emision=date(2024, 1, 15),
        tipo_comprobante="01",
        ruc="1234567890001",
        ambiente="1",
        establecimiento="001",
        punto_emision="001",
        secuencial="000000001",
        codigo_numerico="12345678",
    )
    assert len(clave.value) == 49
    assert clave.value.isdigit()


def test_clave_acceso_invalid_raises():
    import pytest
    with pytest.raises(ValueError):
        ClaveAcceso("123")  # muy corta


def test_clave_acceso_str():
    clave = ClaveAcceso.generate(
        fecha_emision=date(2024, 6, 1),
        tipo_comprobante="01",
        ruc="0912345678001",
        ambiente="2",
        establecimiento="001",
        punto_emision="001",
        secuencial="000000001",
        codigo_numerico="00000001",
    )
    assert str(clave) == clave.value
