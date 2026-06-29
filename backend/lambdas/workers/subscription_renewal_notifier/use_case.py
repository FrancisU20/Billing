from __future__ import annotations

import math
import urllib.error
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Protocol

from lambdas.subscriptions.domain.entities.payment import Payment
from lambdas.subscriptions.domain.repositories.i_dlocal_client import IDLocalClient
from lambdas.subscriptions.domain.repositories.i_payment_repository import IPaymentRepository
from lambdas.subscriptions.domain.repositories.i_plan_catalog import IPlanCatalog
from lambdas.tenants.domain.enums import SubscriptionStatus
from lambdas.tenants.domain.repositories.i_tenant_repository import ITenantRepository
from lambdas.workers.email_notifications.ports import EmailSender
from shared.billing import gross_price, plan_net_price
from shared.dates import isoformat_ecuador, now_utc
from shared.errors import OptimisticLockError
from shared.logger import get_logger

_log = get_logger(__name__)

_NOTIFIER_USER_ID = "system:subscription-renewal-notifier"
_REMINDER_DAYS = 7
_PAYMENT_FAILED_GRACE_DAYS = 7
_SECONDS_PER_DAY = 86400
_COUNTRY = "EC"
_CURRENCY = "USD"


class AutoRenewalReconciliationNotifier(Protocol):
    def send_auto_renewal_reconciliation_alert(
        self,
        *,
        billing_email: str,
        tenant_id: str,
        tenant_email: str,
        trade_name: str,
        order_id: str,
        plan_id: str,
        amount: str,
        currency: str,
        confirmed_at: str,
        reason: str,
    ) -> None: ...


class _AutoRenewalReconciliationRequiredError(Exception):
    pass


@dataclass(frozen=True)
class NotifySubscriptionRenewalResult:
    reminders_sent: int
    expirations_processed: int
    auto_charged: int = field(default=0)
    payment_failed_count: int = field(default=0)
    auto_charge_reconciliation_required_count: int = field(default=0)


class NotifySubscriptionRenewalUseCase:
    def __init__(
        self,
        tenant_repo: ITenantRepository,
        email_sender: EmailSender,
        *,
        now: datetime,
        frontend_url: str = "",
        plan_catalog: IPlanCatalog | None = None,
        dlocal: IDLocalClient | None = None,
        payment_repo: IPaymentRepository | None = None,
        reconciliation_notifier: AutoRenewalReconciliationNotifier | None = None,
        reconciliation_email: str = "",
    ) -> None:
        self._tenant_repo = tenant_repo
        self._email_sender = email_sender
        self._now = now
        self._renewal_url = f"{frontend_url.rstrip('/')}/billing"
        self._plan_catalog = plan_catalog
        self._dlocal = dlocal
        self._payment_repo = payment_repo
        self._reconciliation_notifier = reconciliation_notifier
        self._reconciliation_email = reconciliation_email

    def execute(self) -> NotifySubscriptionRenewalResult:
        before = self._now + timedelta(days=_REMINDER_DAYS)
        candidates = self._tenant_repo.list_with_subscription_expiry_due(before)

        reminders_sent = 0
        expirations_processed = 0
        auto_charged = 0
        payment_failed_count = 0
        auto_charge_reconciliation_required_count = 0

        for tenant in candidates:
            try:
                action = self._process_tenant(tenant)
            except _AutoRenewalReconciliationRequiredError:
                auto_charge_reconciliation_required_count += 1
                _log.error(
                    "auto-charge paid externally but local renewal requires reconciliation",
                    tenant_id=tenant.id,
                )
                continue
            except OptimisticLockError:
                _log.warning(
                    "subscription renewal notifier lost concurrent update; will retry on next run",
                    tenant_id=tenant.id,
                )
                continue
            except Exception:
                _log.error(
                    "unexpected error processing tenant for subscription renewal",
                    tenant_id=tenant.id,
                    exc_info=True,
                )
                continue

            if action == "expired":
                expirations_processed += 1
            elif action == "reminder":
                reminders_sent += 1
            elif action == "auto_charged":
                auto_charged += 1
            elif action == "payment_failed":
                payment_failed_count += 1
            elif action == "auto_charge_reconciliation_required":
                auto_charge_reconciliation_required_count += 1

        return NotifySubscriptionRenewalResult(
            reminders_sent=reminders_sent,
            expirations_processed=expirations_processed,
            auto_charged=auto_charged,
            payment_failed_count=payment_failed_count,
            auto_charge_reconciliation_required_count=(auto_charge_reconciliation_required_count),
        )

    def _process_tenant(self, tenant) -> str | None:
        ends_at = tenant.plan_cycle_ends_at
        if ends_at is None:
            return None

        if ends_at <= self._now:
            if tenant.subscription_status == SubscriptionStatus.PAYMENT_FAILED:
                return self._process_payment_failed(tenant, ends_at)
            if self._can_auto_charge(tenant):
                return self._try_auto_charge(tenant)
            self._do_expire(tenant)
            return "expired"

        # Still active — send reminder if not already sent
        if tenant.subscription_renewal_reminder_sent_at is None:
            days_remaining = max(
                1,
                math.ceil((ends_at - self._now).total_seconds() / _SECONDS_PER_DAY),
            )
            self._email_sender.send_subscription_renewal_reminder(
                email=tenant.email,
                legal_rep_name=tenant.legal_rep_name,
                trade_name=tenant.trade_name,
                plan_cycle_ends_at=isoformat_ecuador(ends_at) or "",
                days_remaining=days_remaining,
                renewal_url=self._renewal_url,
            )
            tenant.mark_renewal_reminder_sent(
                sent_at=self._now,
                updated_by=_NOTIFIER_USER_ID,
            )
            self._tenant_repo.save(tenant, user_id=_NOTIFIER_USER_ID)
            return "reminder"

        return None

    def _do_expire(self, tenant) -> None:
        tenant.expire_subscription(updated_by=_NOTIFIER_USER_ID)
        self._tenant_repo.save(tenant, user_id=_NOTIFIER_USER_ID)
        self._email_sender.send_subscription_expired(
            email=tenant.email,
            legal_rep_name=tenant.legal_rep_name,
            trade_name=tenant.trade_name,
            renewal_url=self._renewal_url,
        )

    def _process_payment_failed(self, tenant, ends_at) -> str:
        grace_expires_at = ends_at + timedelta(days=_PAYMENT_FAILED_GRACE_DAYS)
        if self._now >= grace_expires_at or not self._can_auto_charge(tenant):
            self._do_expire(tenant)
            return "expired"
        return self._try_auto_charge(tenant)

    def _can_auto_charge(self, tenant) -> bool:
        return bool(
            tenant.dlocal_payer_id and self._plan_catalog and self._dlocal and self._payment_repo
        )

    def _try_auto_charge(self, tenant) -> str:
        plan = self._plan_catalog.get(tenant.plan_id)  # type: ignore[union-attr]
        if plan.is_free:
            tenant.expire_subscription(updated_by=_NOTIFIER_USER_ID)
            self._tenant_repo.save(tenant, user_id=_NOTIFIER_USER_ID)
            self._email_sender.send_subscription_expired(
                email=tenant.email,
                legal_rep_name=tenant.legal_rep_name,
                trade_name=tenant.trade_name,
                renewal_url=self._renewal_url,
            )
            return "expired"

        billing_cycle = tenant.billing_cycle
        amount = gross_price(plan_net_price(plan.monthly_price, plan.annual_price, billing_cycle))
        cycle_ends_at = tenant.plan_cycle_ends_at
        if not cycle_ends_at:
            _log.error(
                "auto-charge skipped because tenant has no cycle end date", tenant_id=tenant.id
            )
            return None
        marker_created = self._payment_repo.create_auto_renewal_reconciliation_marker(  # type: ignore[union-attr]
            tenant_id=tenant.id,
            cycle_ends_at=cycle_ends_at,
            plan_id=tenant.plan_id,
            amount=amount,
            currency=_CURRENCY,
            reason="AUTO_RENEWAL_STARTED",
        )
        if not marker_created:
            _log.error(
                "auto-charge skipped because renewal reconciliation is pending",
                tenant_id=tenant.id,
                plan_cycle_ends_at=cycle_ends_at.isoformat(),
            )
            pending_payment = Payment(
                order_id="",
                tenant_id=tenant.id,
                plan_id=tenant.plan_id,
                amount=amount,
                currency=_CURRENCY,
                status="FAILED",
                plan_cycle=billing_cycle,
                confirmed_at=now_utc(),
                payer_id=tenant.dlocal_payer_id,
            )
            self._alert_auto_renewal_reconciliation_required(
                tenant=tenant,
                payment=pending_payment,
                reason="AUTO_RENEWAL_MARKER_EXISTS",
            )
            return "auto_charge_reconciliation_required"

        charge_status = "FAILED"
        payment_id = None
        try:
            result = self._dlocal.charge_saved_payer(  # type: ignore[union-attr]
                tenant.dlocal_payer_id, amount, _CURRENCY, _COUNTRY
            )
            charge_status = result.status
            payment_id = result.payment_id
        except (urllib.error.HTTPError, urllib.error.URLError) as exc:
            _log.warning(
                "auto-charge dLocal request failed",
                tenant_id=tenant.id,
                exc_info=True,
            )
            payment = Payment(
                order_id="",
                tenant_id=tenant.id,
                plan_id=tenant.plan_id,
                amount=amount,
                currency=_CURRENCY,
                status="FAILED",
                plan_cycle=billing_cycle,
                confirmed_at=now_utc(),
                payer_id=tenant.dlocal_payer_id,
                error_detail=type(exc).__name__,
            )
            self._record_auto_renewal_reconciliation_required(
                tenant=tenant,
                payment=payment,
                cycle_ends_at=cycle_ends_at,
                reason=type(exc).__name__,
            )
            raise _AutoRenewalReconciliationRequiredError() from exc

        if charge_status == "PAID":
            now = now_utc()
            payment = Payment(
                order_id=payment_id or "",
                tenant_id=tenant.id,
                plan_id=tenant.plan_id,
                amount=amount,
                currency=_CURRENCY,
                status="PAID",
                plan_cycle=billing_cycle,
                confirmed_at=now,
                payer_id=tenant.dlocal_payer_id,
            )
            tenant.apply_subscription_renewal(
                payer_id=tenant.dlocal_payer_id,
                plan_cycle=billing_cycle,
                now=now,
                updated_by=_NOTIFIER_USER_ID,
            )
            payment_transact = self._payment_repo.save_transact_item(payment)  # type: ignore[union-attr]
            try:
                self._tenant_repo.commit(
                    tenant=tenant,
                    user_id=_NOTIFIER_USER_ID,
                    action="SUBSCRIPTION_AUTO_RENEWAL",
                    events=[],
                    idempotency=None,
                    response=None,
                    extra_transact_items=[payment_transact],
                )
            except Exception as exc:
                self._record_auto_renewal_reconciliation_required(
                    tenant=tenant,
                    payment=payment,
                    cycle_ends_at=cycle_ends_at,
                    reason=type(exc).__name__,
                )
                raise _AutoRenewalReconciliationRequiredError() from exc
            _log.info(
                "auto-charge succeeded",
                tenant_id=tenant.id,
                order_id=payment_id,
                amount=amount,
            )
            self._delete_auto_renewal_reconciliation_marker(
                tenant_id=tenant.id,
                cycle_ends_at=cycle_ends_at,
                order_id=payment.order_id,
            )
            return "auto_charged"
        else:
            was_already_failed = tenant.subscription_status == SubscriptionStatus.PAYMENT_FAILED
            tenant.mark_payment_failed(updated_by=_NOTIFIER_USER_ID)
            self._tenant_repo.save(tenant, user_id=_NOTIFIER_USER_ID)
            self._delete_auto_renewal_reconciliation_marker(
                tenant_id=tenant.id,
                cycle_ends_at=cycle_ends_at,
                order_id=payment_id or "",
            )
            if not was_already_failed:
                self._email_sender.send_payment_failed(
                    email=tenant.email,
                    legal_rep_name=tenant.legal_rep_name,
                    trade_name=tenant.trade_name,
                    renewal_url=self._renewal_url,
                )
            _log.warning(
                "auto-charge rejected",
                tenant_id=tenant.id,
                dlocal_status=charge_status,
                repeated=was_already_failed,
            )
            return "payment_failed"

    def _delete_auto_renewal_reconciliation_marker(
        self,
        *,
        tenant_id: str,
        cycle_ends_at: datetime,
        order_id: str,
    ) -> None:
        try:
            self._payment_repo.delete_auto_renewal_reconciliation_marker(  # type: ignore[union-attr]
                tenant_id=tenant_id,
                cycle_ends_at=cycle_ends_at,
            )
        except Exception:
            _log.error(
                "failed to clear auto renewal reconciliation marker",
                tenant_id=tenant_id,
                order_id=order_id,
                exc_info=True,
            )

    def _record_auto_renewal_reconciliation_required(
        self,
        *,
        tenant,
        payment: Payment,
        cycle_ends_at: datetime | None,
        reason: str,
    ) -> None:
        if cycle_ends_at is None:
            _log.error(
                "cannot create auto renewal reconciliation marker without cycle end date",
                tenant_id=tenant.id,
                order_id=payment.order_id,
                reason=reason,
            )
        else:
            try:
                self._payment_repo.save_auto_renewal_reconciliation_marker(  # type: ignore[union-attr]
                    payment,
                    tenant_id=tenant.id,
                    cycle_ends_at=cycle_ends_at,
                    reason=reason,
                )
            except Exception:
                _log.error(
                    "failed to persist auto renewal reconciliation marker",
                    tenant_id=tenant.id,
                    order_id=payment.order_id,
                    exc_info=True,
                )

        self._alert_auto_renewal_reconciliation_required(
            tenant=tenant,
            payment=payment,
            reason=reason,
        )

    def _alert_auto_renewal_reconciliation_required(
        self,
        *,
        tenant,
        payment: Payment,
        reason: str,
    ) -> None:
        if not self._reconciliation_notifier or not self._reconciliation_email:
            _log.error(
                "auto renewal reconciliation alert not configured",
                tenant_id=tenant.id,
                order_id=payment.order_id,
                reason=reason,
            )
            return

        try:
            self._reconciliation_notifier.send_auto_renewal_reconciliation_alert(
                billing_email=self._reconciliation_email,
                tenant_id=tenant.id,
                tenant_email=tenant.email,
                trade_name=tenant.trade_name,
                order_id=payment.order_id,
                plan_id=payment.plan_id,
                amount=payment.amount,
                currency=payment.currency,
                confirmed_at=isoformat_ecuador(payment.confirmed_at) or "",
                reason=reason,
            )
        except Exception:
            _log.error(
                "failed to send auto renewal reconciliation alert",
                tenant_id=tenant.id,
                order_id=payment.order_id,
                exc_info=True,
            )
