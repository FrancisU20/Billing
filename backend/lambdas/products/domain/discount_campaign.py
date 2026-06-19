from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from shared.dates import isoformat_ecuador
from shared.domain.base_entity import TenantScopedEntity
from shared.errors import ValidationError

_SINGLETON_ID = "default"


@dataclass
class DiscountCampaign(TenantScopedEntity):
    active: bool = False
    percentage: Decimal = Decimal("0.00")

    @classmethod
    def default(cls, tenant_id: str) -> DiscountCampaign:
        return cls(id=_SINGLETON_ID, tenant_id=tenant_id, active=False, percentage=Decimal("0.00"))

    def update(self, *, active: bool, percentage: Decimal, updated_by: str) -> None:
        self.active = active
        self.percentage = _percentage(percentage)
        self.touch(updated_by)

    def to_dict(self) -> dict:
        return {
            "active": self.active,
            "percentage": str(self.percentage),
            "updated_at": isoformat_ecuador(self.updated_at),
            "updated_by": self.updated_by,
            "version": self.version,
        }


def _percentage(value: Decimal) -> Decimal:
    amount = Decimal(str(value)).quantize(Decimal("0.01"))
    if amount < 0 or amount > 100:
        raise ValidationError("El porcentaje de la campaña debe estar entre 0 y 100%")
    return amount
