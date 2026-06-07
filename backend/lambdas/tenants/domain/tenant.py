from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from lambdas.tenants.domain.commands import CreateTenantCommand, UpdateTenantCommand
from lambdas.tenants.domain.enums import PlanStatus, SriEnvironment, TenantStatus
from lambdas.tenants.domain.errors import InvalidSriEnvironmentError
from shared.domain.base_entity import GlobalEntity
from shared.domain.value_objects.email import Email
from shared.domain.value_objects.ruc import RUC


@dataclass
class Tenant(GlobalEntity):
    ruc: str = ""
    trade_name: str = ""
    legal_rep_name: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    sri_environment: SriEnvironment = field(default=SriEnvironment.TESTING)
    status: TenantStatus = field(default=TenantStatus.ACTIVE)
    plan_id: str = ""
    plan_status: PlanStatus = field(default=PlanStatus.ACTIVE)
    trial_ends_at: datetime | None = None

    # ── factory ───────────────────────────────────────────────────────────────

    @classmethod
    def create(cls, cmd: CreateTenantCommand) -> Tenant:
        ruc = RUC(cmd.ruc)
        email = Email(cmd.email)
        return cls(
            ruc=str(ruc),
            trade_name=cmd.trade_name.strip(),
            legal_rep_name=cmd.legal_rep_name.strip(),
            email=str(email),
            phone=cmd.phone.strip(),
            address=cmd.address.strip(),
            sri_environment=SriEnvironment.TESTING,
            status=TenantStatus.ACTIVE,
            plan_id=cmd.plan_id,
            plan_status=PlanStatus.ACTIVE,
            trial_ends_at=None,
            created_by=cmd.created_by,
            updated_by=cmd.created_by,
        )

    # ── domain behaviour ──────────────────────────────────────────────────────

    def update(self, cmd: UpdateTenantCommand) -> None:
        if cmd.trade_name is not None:
            self.trade_name = cmd.trade_name.strip()
        if cmd.legal_rep_name is not None:
            self.legal_rep_name = cmd.legal_rep_name.strip()
        if cmd.email is not None:
            self.email = str(Email(cmd.email))
        if cmd.phone is not None:
            self.phone = cmd.phone.strip()
        if cmd.address is not None:
            self.address = cmd.address.strip()
        if cmd.sri_environment is not None:
            try:
                self.sri_environment = SriEnvironment(cmd.sri_environment)
            except ValueError:
                raise InvalidSriEnvironmentError()
        self.touch(cmd.updated_by)

    def change_status(self, new_status: TenantStatus, updated_by: str) -> None:
        self.status = new_status
        self.touch(updated_by)

    def is_active(self) -> bool:
        return self.status == TenantStatus.ACTIVE

    # ── serialisation ─────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "ruc": self.ruc,
            "trade_name": self.trade_name,
            "legal_rep_name": self.legal_rep_name,
            "email": self.email,
            "phone": self.phone,
            "address": self.address,
            "sri_environment": self.sri_environment.value,
            "status": self.status.value,
            "plan_id": self.plan_id,
            "plan_status": self.plan_status.value,
            "trial_ends_at": self.trial_ends_at.isoformat() if self.trial_ends_at else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
            "version": self.version,
        }
