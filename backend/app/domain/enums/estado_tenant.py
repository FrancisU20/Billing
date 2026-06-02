from enum import StrEnum


class EstadoTenant(StrEnum):
    TRIAL = "TRIAL"
    ACTIVE = "ACTIVE"
    PAYMENT_DUE = "PAYMENT_DUE"
    GRACE_PERIOD = "GRACE_PERIOD"
    SUSPENDED = "SUSPENDED"
    CANCELLED = "CANCELLED"

    @property
    def can_emit(self) -> bool:
        """Indica si el tenant puede emitir comprobantes en este estado."""
        return self in {EstadoTenant.TRIAL, EstadoTenant.ACTIVE, EstadoTenant.GRACE_PERIOD}
