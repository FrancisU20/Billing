from __future__ import annotations

"""Ordered migration registry."""

from migrations.definition import Migration
from migrations.versions import (
    v0001_seed_plans,
    v0002_backfill_plan_cycle_ends_at,
    v0003_backfill_onboarding_fields,
    v0004_update_plan_catalog,
    v0005_backfill_product_invoice_code,
)

MIGRATIONS: tuple[Migration, ...] = (
    Migration(
        id=v0001_seed_plans.MIGRATION_ID,
        description=v0001_seed_plans.DESCRIPTION,
        run=v0001_seed_plans.run,
    ),
    Migration(
        id=v0002_backfill_plan_cycle_ends_at.MIGRATION_ID,
        description=v0002_backfill_plan_cycle_ends_at.DESCRIPTION,
        run=v0002_backfill_plan_cycle_ends_at.run,
    ),
    Migration(
        id=v0003_backfill_onboarding_fields.MIGRATION_ID,
        description=v0003_backfill_onboarding_fields.DESCRIPTION,
        run=v0003_backfill_onboarding_fields.run,
    ),
    Migration(
        id=v0004_update_plan_catalog.MIGRATION_ID,
        description=v0004_update_plan_catalog.DESCRIPTION,
        run=v0004_update_plan_catalog.run,
    ),
    Migration(
        id=v0005_backfill_product_invoice_code.MIGRATION_ID,
        description=v0005_backfill_product_invoice_code.DESCRIPTION,
        run=v0005_backfill_product_invoice_code.run,
    ),
)
