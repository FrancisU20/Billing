from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CreatePlanCommand:
    slug:                str    # immutable — not in UpdatePlanCommand
    name:                str
    description:         str
    monthly_price:       float
    annual_price:        float
    document_limit:      int
    limit_cycle:         str
    max_locations:       int
    max_emission_points: int
    max_users:           int
    includes_credit_notes:   bool
    includes_withholdings:   bool
    includes_delivery_notes: bool
    includes_api:            bool
    order:               int
    created_by:          str


@dataclass
class UpdatePlanCommand:
    id:                  str    # plan UUID
    updated_by:          str
    # slug is immutable — cannot be updated
    name:                str | None = None
    description:         str | None = None
    monthly_price:       float | None = None
    annual_price:        float | None = None
    document_limit:      int | None = None
    limit_cycle:         str | None = None
    max_locations:       int | None = None
    max_emission_points: int | None = None
    max_users:           int | None = None
    includes_credit_notes:   bool | None = None
    includes_withholdings:   bool | None = None
    includes_delivery_notes: bool | None = None
    includes_api:            bool | None = None
    order:               int | None = None


@dataclass
class TogglePlanCommand:
    id:         str    # plan UUID
    active:     bool
    updated_by: str
