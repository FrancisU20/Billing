from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from dateutil.relativedelta import relativedelta

from lambdas.tenants.domain.commands import CreateTenantCommand, UpdateTenantCommand
from lambdas.tenants.domain.enums import PlanStatus, SriEnvironment, TenantStatus
from lambdas.tenants.domain.errors import InvalidSriEnvironmentError
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
            except ValueError:
                raise InvalidSriEnvironmentError()
        self.touch(cmd.updated_by)

    def change_status(self, new_status: TenantStatus, updated_by: str) -> None:
        allowed = _ALLOWED_STATUS_TRANSITIONS[self.status]
        if new_status not in allowed:
            raise ValidationError("Transición de estado inválida")
        self.status = new_status
        self.touch(updated_by)

    def is_active(self) -> bool:
        return self.status == TenantStatus.ACTIVE

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
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
            "version": self.version,
        }
