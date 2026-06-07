from __future__ import annotations

"""Shared migration value objects."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MigrationContext:
    tables: dict[str, Any]

    def table(self, name: str):
        return self.tables[name]


@dataclass(frozen=True)
class MigrationResult:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    details: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "created": self.created,
            "updated": self.updated,
            "skipped": self.skipped,
            "details": self.details,
        }
