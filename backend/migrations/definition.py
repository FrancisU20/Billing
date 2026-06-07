from __future__ import annotations

"""Migration definition shared by registry and runner ports."""

from collections.abc import Callable
from dataclasses import dataclass

from migrations.context import MigrationContext, MigrationResult


@dataclass(frozen=True)
class Migration:
    id: str
    description: str
    run: Callable[[MigrationContext], MigrationResult]
