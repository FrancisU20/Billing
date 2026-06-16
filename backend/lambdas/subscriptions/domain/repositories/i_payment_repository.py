from __future__ import annotations

from abc import ABC, abstractmethod

from lambdas.subscriptions.domain.entities.payment import Payment


class IPaymentRepository(ABC):
    @abstractmethod
    def save(self, payment: Payment) -> None: ...

    @abstractmethod
    def get_by_order_id(self, order_id: str) -> Payment: ...
