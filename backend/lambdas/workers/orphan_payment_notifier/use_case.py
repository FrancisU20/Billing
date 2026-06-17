from __future__ import annotations

"""Orphan payment notifier — alertas de pagos PAID sin tenant vinculado.

Un pago huérfano ocurre cuando dLocal confirmó el cobro (status=PAID) pero el
paso de creación de tenant (/otp/confirm) falló antes de vincular el payment al
tenant. El cliente fue cobrado sin que se le creara la cuenta.

Este use case escanea la tabla payments buscando pagos PAID con tenant_id
ausente que ya superaron el grace period, y notifica al superadmin por email.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from lambdas.workers.email_notifications.ports import EmailSender
from shared.logger import get_logger

_log = get_logger(__name__)


@dataclass(frozen=True)
class OrphanPaymentSummary:
    order_id: str
    payer_email: str | None
    plan_id: str
    amount: str
    currency: str
    confirmed_at: str


class IOrphanPaymentQuery(ABC):
    @abstractmethod
    def list_orphaned_paid(self, *, cutoff: datetime) -> list[OrphanPaymentSummary]:
        """Return PAID payments with no tenant_id confirmed before the cutoff datetime."""


@dataclass(frozen=True)
class NotifyOrphanPaymentsResult:
    alerts_sent: int


class NotifyOrphanPaymentsUseCase:
    def __init__(
        self,
        query: IOrphanPaymentQuery,
        email_sender: EmailSender,
        *,
        superadmin_email: str,
        now: datetime,
    ) -> None:
        self._query = query
        self._email_sender = email_sender
        self._superadmin_email = superadmin_email
        self._now = now

    def execute(self) -> NotifyOrphanPaymentsResult:
        orphans = self._query.list_orphaned_paid(cutoff=self._now)
        alerts_sent = 0

        for payment in orphans:
            try:
                self._email_sender.send_orphan_payment_alert(
                    superadmin_email=self._superadmin_email,
                    order_id=payment.order_id,
                    payer_email=payment.payer_email,
                    plan_id=payment.plan_id,
                    amount=payment.amount,
                    currency=payment.currency,
                    confirmed_at=payment.confirmed_at,
                )
                alerts_sent += 1
            except Exception:
                _log.error(
                    "orphan payment notifier: failed to send alert",
                    order_id=payment.order_id,
                    exc_info=True,
                )
                continue

        return NotifyOrphanPaymentsResult(alerts_sent=alerts_sent)
