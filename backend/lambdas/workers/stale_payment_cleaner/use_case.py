from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from lambdas.subscriptions.domain.entities.payment import Payment
from shared.logger import get_logger

_log = get_logger(__name__)


class StalePaymentRepository(Protocol):
    def list_stale_open_payments(self, *, cutoff: datetime) -> list[Payment]: ...

    def cancel_stale_open_payment(self, *, order_id: str, cutoff: datetime) -> bool: ...


@dataclass(frozen=True)
class CleanStalePaymentsResult:
    candidates: int
    cancelled: int
    skipped: int
    errors: int


class CleanStalePaymentsUseCase:
    def __init__(
        self,
        payment_repo: StalePaymentRepository,
        *,
        now: datetime,
        grace_minutes: int,
    ) -> None:
        self._payment_repo = payment_repo
        self._now = now
        self._grace_minutes = grace_minutes

    def execute(self) -> CleanStalePaymentsResult:
        cutoff = self._now - timedelta(minutes=self._grace_minutes)
        candidates = self._payment_repo.list_stale_open_payments(cutoff=cutoff)
        cancelled = skipped = errors = 0

        for payment in candidates:
            try:
                if self._payment_repo.cancel_stale_open_payment(
                    order_id=payment.order_id,
                    cutoff=cutoff,
                ):
                    cancelled += 1
                    _log.info(
                        "stale payment cancelled",
                        order_id=payment.order_id,
                        status=payment.status,
                    )
                else:
                    skipped += 1
                    _log.info(
                        "stale payment skipped after conditional check",
                        order_id=payment.order_id,
                        status=payment.status,
                    )
            except Exception:
                errors += 1
                _log.error(
                    "stale payment cleaner failed to cancel payment",
                    order_id=payment.order_id,
                    status=payment.status,
                    exc_info=True,
                )

        return CleanStalePaymentsResult(
            candidates=len(candidates),
            cancelled=cancelled,
            skipped=skipped,
            errors=errors,
        )
