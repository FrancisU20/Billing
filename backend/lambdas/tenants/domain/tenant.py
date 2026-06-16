from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from dateutil.relativedelta import relativedelta

from lambdas.tenants.domain.commands import CreateTenantCommand, UpdateTenantCommand
from lambdas.tenants.domain.enums import PlanStatus, SriEnvironment, TenantStatus
from lambdas.tenants.domain.errors import InvalidSriEnvironmentError
from shared.certificates.expiry import CERTIFICATE_EXPIRY_ALERT_THRESHOLDS_DAYS
from shared.certificates.metadata import CertificateMetadata
from shared.domain.base_entity import GlobalEntity
from shared.domain.value_objects.email import Email
from shared.domain.value_objects.ruc import RUC
from shared.errors import ValidationError


def _cycle_duration(limit_cycle: str) -> relativedelta:
    return relativedelta(years=1) if limit_cycle == "year" else relativedelta(months=1)


_ALLOWED_STATUS_TRANSITIONS: dict[TenantStatus, set[TenantStatus]] = {
    TenantStatus.ACTIVE: {
        TenantStatus.ACTIVE,
        TenantStatus.SUSPENDED,
        TenantStatus.INACTIVE,
    },
    TenantStatus.SUSPENDED: {
        TenantStatus.ACTIVE,
        TenantStatus.SUSPENDED,
        TenantStatus.INACTIVE,
    },
    TenantStatus.INACTIVE: {
        TenantStatus.ACTIVE,
        TenantStatus.INACTIVE,
    },
}


def _certificate_expiry_alert_attr(threshold_days: int) -> str:
    if threshold_days not in CERTIFICATE_EXPIRY_ALERT_THRESHOLDS_DAYS:
        raise ValueError(f"umbral de alerta no soportado: {threshold_days}")
    return f"cert_expiry_alert_{threshold_days}_sent_at"


@dataclass
class Tenant(GlobalEntity):
    ruc: str = ""
    trade_name: str = ""
    legal_name: str = ""
    legal_rep_name: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    accounting_required: bool = False
    sri_environment: SriEnvironment = field(default=SriEnvironment.TESTING)
    status: TenantStatus = field(default=TenantStatus.ACTIVE)
    plan_id: str = ""
    plan_cycle_ends_at: datetime | None = None
    certificate_secret_arn: str | None = None
    cert_subject_ruc: str | None = None
    cert_expires_at: datetime | None = None
    cert_issuer: str | None = None
    cert_uploaded_at: datetime | None = None
    cert_expiry_alert_60_sent_at: datetime | None = None
    cert_expiry_alert_30_sent_at: datetime | None = None
    onboarding_completed_at: datetime | None = None
    dlocal_payer_id: str | None = None
    subscription_status: str | None = None
    subscription_renewal_reminder_sent_at: datetime | None = None

    # ── factory ───────────────────────────────────────────────────────────────

    @classmethod
    def create(cls, cmd: CreateTenantCommand, *, plan_limit_cycle: str) -> Tenant:
        ruc = RUC(cmd.ruc)
        email = Email(cmd.email)
        tenant = cls(
            ruc=str(ruc),
            trade_name=cmd.trade_name.strip(),
            legal_name=cmd.legal_name.strip(),
            legal_rep_name=cmd.legal_rep_name.strip(),
            email=str(email),
            phone=cmd.phone.strip(),
            address=cmd.address.strip(),
            accounting_required=cmd.accounting_required,
            sri_environment=SriEnvironment.TESTING,
            status=TenantStatus.ACTIVE,
            plan_id=cmd.plan_id,
            created_by=cmd.created_by,
            updated_by=cmd.created_by,
        )
        tenant.plan_cycle_ends_at = tenant.created_at + _cycle_duration(plan_limit_cycle)
        return tenant

    # ── domain behaviour ──────────────────────────────────────────────────────

    def update(self, cmd: UpdateTenantCommand) -> None:
        if cmd.trade_name is not None:
            self.trade_name = cmd.trade_name.strip()
        if cmd.legal_name is not None:
            self.legal_name = cmd.legal_name.strip()
        if cmd.legal_rep_name is not None:
            self.legal_rep_name = cmd.legal_rep_name.strip()
        if cmd.email is not None:
            self.email = str(Email(cmd.email))
        if cmd.phone is not None:
            self.phone = cmd.phone.strip()
        if cmd.address is not None:
            self.address = cmd.address.strip()
        if cmd.accounting_required is not None:
            self.accounting_required = cmd.accounting_required
        if cmd.sri_environment is not None:
            try:
                self.sri_environment = SriEnvironment(cmd.sri_environment)
            except ValueError as exc:
                raise InvalidSriEnvironmentError() from exc
        self.touch(cmd.updated_by)

    def change_status(self, new_status: TenantStatus, updated_by: str) -> None:
        allowed = _ALLOWED_STATUS_TRANSITIONS[self.status]
        if new_status not in allowed:
            raise ValidationError("Transición de estado inválida")
        self.status = new_status
        self.touch(updated_by)

    def is_active(self) -> bool:
        return self.status == TenantStatus.ACTIVE

    def attach_certificate(
        self,
        metadata: CertificateMetadata,
        *,
        secret_arn: str,
        uploaded_at: datetime,
        updated_by: str,
        complete_onboarding: bool = False,
        touch_entity: bool = True,
    ) -> None:
        self.certificate_secret_arn = secret_arn
        self.cert_subject_ruc = metadata.subject_ruc
        self.cert_expires_at = metadata.expires_at
        self.cert_issuer = metadata.issuer
        self.cert_uploaded_at = uploaded_at
        # A new certificate starts a fresh expiry-alert cycle.
        for threshold in CERTIFICATE_EXPIRY_ALERT_THRESHOLDS_DAYS:
            setattr(self, _certificate_expiry_alert_attr(threshold), None)
        if complete_onboarding and self.onboarding_completed_at is None:
            self.onboarding_completed_at = uploaded_at
        if touch_entity:
            self.touch(updated_by)

    def due_certificate_expiry_alerts(self, now: datetime) -> list[int]:
        if self.cert_expires_at is None:
            return []
        return [
            threshold
            for threshold in CERTIFICATE_EXPIRY_ALERT_THRESHOLDS_DAYS
            if getattr(self, _certificate_expiry_alert_attr(threshold)) is None
            and now >= self.cert_expires_at - timedelta(days=threshold)
        ]

    def apply_subscription_renewal(
        self, *, payer_id: str, plan_cycle: str, now: datetime, updated_by: str
    ) -> None:
        base = max(now, self.plan_cycle_ends_at) if self.plan_cycle_ends_at else now
        self.plan_cycle_ends_at = base + _cycle_duration(plan_cycle)
        self.dlocal_payer_id = payer_id
        self.subscription_status = "active"
        self.subscription_renewal_reminder_sent_at = None
        if self.status == TenantStatus.SUSPENDED:
            self.status = TenantStatus.ACTIVE
        self.touch(updated_by)

    def expire_subscription(self, *, updated_by: str) -> None:
        self.subscription_status = "expired"
        self.status = TenantStatus.SUSPENDED
        self.touch(updated_by)

    def mark_renewal_reminder_sent(self, *, sent_at: datetime, updated_by: str) -> None:
        self.subscription_renewal_reminder_sent_at = sent_at
        self.touch(updated_by)

    def mark_certificate_expiry_alert_sent(
        self, threshold_days: int, sent_at: datetime, updated_by: str
    ) -> None:
        setattr(self, _certificate_expiry_alert_attr(threshold_days), sent_at)
        self.touch(updated_by)

    def effective_plan_status(self, now: datetime) -> PlanStatus:
        """Computed, never persisted — there is nothing to drift out of sync.

        A plan expires once its cycle ends. (Extension point for when the
        `invoices` Lambda exists: add `documents_issued >= plan.document_limit`
        as a second condition — expiration triggers on whichever comes first.)
        """
        if self.plan_cycle_ends_at and now >= self.plan_cycle_ends_at:
            return PlanStatus.EXPIRED
        return PlanStatus.ACTIVE

    # ── serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "ruc": self.ruc,
            "trade_name": self.trade_name,
            "legal_name": self.legal_name,
            "legal_rep_name": self.legal_rep_name,
            "email": self.email,
            "phone": self.phone,
            "address": self.address,
            "accounting_required": self.accounting_required,
            "sri_environment": self.sri_environment.value,
            "status": self.status.value,
            "plan_id": self.plan_id,
            "plan_status": self.effective_plan_status(datetime.now(UTC)).value,
            "plan_cycle_ends_at": (
                self.plan_cycle_ends_at.isoformat() if self.plan_cycle_ends_at else None
            ),
            "cert_subject_ruc": self.cert_subject_ruc,
            "cert_expires_at": self.cert_expires_at.isoformat() if self.cert_expires_at else None,
            "cert_issuer": self.cert_issuer,
            "cert_uploaded_at": (
                self.cert_uploaded_at.isoformat() if self.cert_uploaded_at else None
            ),
            "cert_expiry_alert_60_sent_at": (
                self.cert_expiry_alert_60_sent_at.isoformat()
                if self.cert_expiry_alert_60_sent_at
                else None
            ),
            "cert_expiry_alert_30_sent_at": (
                self.cert_expiry_alert_30_sent_at.isoformat()
                if self.cert_expiry_alert_30_sent_at
                else None
            ),
            "onboarding_completed_at": (
                self.onboarding_completed_at.isoformat() if self.onboarding_completed_at else None
            ),
            "dlocal_payer_id": self.dlocal_payer_id,
            "subscription_status": self.subscription_status,
            "subscription_renewal_reminder_sent_at": (
                self.subscription_renewal_reminder_sent_at.isoformat()
                if self.subscription_renewal_reminder_sent_at
                else None
            ),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
            "version": self.version,
        }
