from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class InvoiceProductSnapshot:
    product_id: str
    code: str
    description: str
    unit_price: Decimal
    iva_rate: str


class IProductCatalog(ABC):
    @abstractmethod
    def get_active_snapshot(self, product_id: str) -> InvoiceProductSnapshot:
        """Return invoice snapshot for an active product."""
