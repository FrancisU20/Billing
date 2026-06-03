# Re-export desde domain — la fuente de verdad vive en app.domain.schemas.factura
from app.domain.schemas.factura import (  # noqa: F401
    DatosFactura,
    DetalleFactura,
    ImpuestoDetalle,
    PagoFactura,
)
