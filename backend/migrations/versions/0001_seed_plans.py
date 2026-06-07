from __future__ import annotations

"""Compatibility wrapper for local manual execution of v0001_seed_plans."""

import os

import boto3

from migrations.context import MigrationContext
from migrations.versions.v0001_seed_plans import DESCRIPTION, MIGRATION_ID, run


def main() -> None:
    context = MigrationContext(
        tables={
            "PLANS_TABLE": boto3.resource("dynamodb").Table(os.environ["PLANS_TABLE"]),
        }
    )
    result = run(context)
    print(f"{MIGRATION_ID} — {DESCRIPTION}")
    print(result.to_dict())


if __name__ == "__main__":
    main()
