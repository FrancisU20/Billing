from __future__ import annotations

"""Ordered migration registry."""

from migrations.definition import Migration
from migrations.versions import v0001_seed_plans

MIGRATIONS: tuple[Migration, ...] = (
    Migration(
        id=v0001_seed_plans.MIGRATION_ID,
        description=v0001_seed_plans.DESCRIPTION,
        run=v0001_seed_plans.run,
    ),
)
