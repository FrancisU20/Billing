from __future__ import annotations

"""
EnterpriseLead entity — "lead capture" for Enterprise plan signups.

Created instead of a Tenant when the selected Plan has `self_service=False`
(only the Enterprise plan, see `lambdas.plans.domain.plan.Plan`). It is not a
tenant: it does not get a RUC lock, no Cognito user is provisioned, and it does
not appear in `lambdas.tenants`. A superadmin converts it to a real Tenant
manually (out of scope for this phase — see context/ONBOARDING.md).
"""

from dataclasses import dataclass

from lambdas.onboarding.domain.commands import ConfirmOnboardingOtpCommand
from shared.domain.base_entity import GlobalEntity
from shared.domain.value_objects.email import Email
from shared.domain.value_objects.ruc import RUC


@dataclass
class EnterpriseLead(GlobalEntity):
    ruc: str = ""
    trade_name: str = ""
    legal_name: str = ""
    legal_rep_name: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    accounting_required: bool = False
    plan_id: str = ""

    @classmethod
    def create(cls, cmd: ConfirmOnboardingOtpCommand, *, plan_id: str) -> EnterpriseLead:
        ruc = RUC(cmd.ruc)
        email = Email(cmd.email)
        return cls(
            ruc=str(ruc),
            trade_name=cmd.trade_name.strip(),
            legal_name=cmd.legal_name.strip(),
            legal_rep_name=cmd.legal_rep_name.strip(),
            email=str(email),
            phone=cmd.phone.strip(),
            address=cmd.address.strip(),
            accounting_required=cmd.accounting_required,
            plan_id=plan_id,
            created_by="onboarding",
            updated_by="onboarding",
        )

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
            "plan_id": self.plan_id,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
        }
