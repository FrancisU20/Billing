"""
Plan entity — SaaS subscription tiers.

id:   auto-generated UUID — immutable PK, FK in Tenant.plan_id.
slug: human-readable identifier ("free", "basic") — indexed via GSI.
      Immutable after creation. If the slug ever needs changing, only
      this field is updated; no tenant records need to change.

Limits: -1 = unlimited.
limit_cycle: "month" | "year"  (free plan uses "year": 20 docs/year).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from lambdas.plans.domain.commands import CreatePlanCommand, UpdatePlanCommand


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid4())


@dataclass
class Plan:
    id:                  str   = field(default_factory=_uuid)
    slug:                str   = ""
    name:                str   = ""
    description:         str   = ""
    monthly_price:       float = 0.0
    annual_price:        float = 0.0
    document_limit:      int   = 0      # -1 = unlimited
    limit_cycle:         str   = "month"  # "month" | "year"
    max_locations:       int   = 1      # -1 = unlimited
    max_emission_points: int   = 1      # -1 = unlimited
    max_users:           int   = 1      # -1 = unlimited
    includes_credit_notes:   bool = True
    includes_withholdings:   bool = True
    includes_delivery_notes: bool = True
    includes_api:            bool = False
    active:              bool  = True
    order:               int   = 0
    version:             int   = 1
    created_at:          datetime = field(default_factory=_now)
    updated_at:          datetime = field(default_factory=_now)
    created_by:          str   = ""
    updated_by:          str   = ""

    @classmethod
    def create(cls, cmd: CreatePlanCommand) -> "Plan":
        return cls(
            slug                   = cmd.slug,
            name                   = cmd.name.strip(),
            description            = cmd.description.strip(),
            monthly_price          = cmd.monthly_price,
            annual_price           = cmd.annual_price,
            document_limit         = cmd.document_limit,
            limit_cycle            = cmd.limit_cycle,
            max_locations          = cmd.max_locations,
            max_emission_points    = cmd.max_emission_points,
            max_users              = cmd.max_users,
            includes_credit_notes  = cmd.includes_credit_notes,
            includes_withholdings  = cmd.includes_withholdings,
            includes_delivery_notes = cmd.includes_delivery_notes,
            includes_api           = cmd.includes_api,
            order                  = cmd.order,
            created_by             = cmd.created_by,
            updated_by             = cmd.created_by,
        )

    def update(self, cmd: UpdatePlanCommand) -> None:
        if cmd.name is not None:
            self.name = cmd.name.strip()
        if cmd.description is not None:
            self.description = cmd.description.strip()
        if cmd.monthly_price is not None:
            self.monthly_price = cmd.monthly_price
        if cmd.annual_price is not None:
            self.annual_price = cmd.annual_price
        if cmd.document_limit is not None:
            self.document_limit = cmd.document_limit
        if cmd.limit_cycle is not None:
            self.limit_cycle = cmd.limit_cycle
        if cmd.max_locations is not None:
            self.max_locations = cmd.max_locations
        if cmd.max_emission_points is not None:
            self.max_emission_points = cmd.max_emission_points
        if cmd.max_users is not None:
            self.max_users = cmd.max_users
        if cmd.includes_credit_notes is not None:
            self.includes_credit_notes = cmd.includes_credit_notes
        if cmd.includes_withholdings is not None:
            self.includes_withholdings = cmd.includes_withholdings
        if cmd.includes_delivery_notes is not None:
            self.includes_delivery_notes = cmd.includes_delivery_notes
        if cmd.includes_api is not None:
            self.includes_api = cmd.includes_api
        if cmd.order is not None:
            self.order = cmd.order
        self.updated_at  = _now()
        self.updated_by  = cmd.updated_by
        self.version    += 1

    def toggle(self, active: bool, updated_by: str) -> None:
        self.active     = active
        self.updated_at = _now()
        self.updated_by = updated_by
        self.version   += 1

    def to_dict(self) -> dict:
        return {
            "id":                    self.id,
            "slug":                  self.slug,
            "name":                  self.name,
            "description":           self.description,
            "monthly_price":         self.monthly_price,
            "annual_price":          self.annual_price,
            "document_limit":        self.document_limit,
            "limit_cycle":           self.limit_cycle,
            "max_locations":         self.max_locations,
            "max_emission_points":   self.max_emission_points,
            "max_users":             self.max_users,
            "includes_credit_notes":    self.includes_credit_notes,
            "includes_withholdings":    self.includes_withholdings,
            "includes_delivery_notes":  self.includes_delivery_notes,
            "includes_api":          self.includes_api,
            "active":                self.active,
            "order":                 self.order,
            "version":               self.version,
            "created_at":            self.created_at.isoformat(),
            "updated_at":            self.updated_at.isoformat(),
            "created_by":            self.created_by,
        }
