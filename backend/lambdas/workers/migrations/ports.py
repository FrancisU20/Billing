from __future__ import annotations

"""Ports for the migrations worker."""

from abc import ABC, abstractmethod

from migrations.context import MigrationResult
from migrations.definition import Migration


class MigrationStateRepository(ABC):
    @abstractmethod
    def begin(self, migration: Migration) -> bool:
        """Return True when this invocation should run the migration."""

    @abstractmethod
    def mark_succeeded(self, migration: Migration, result: MigrationResult) -> None:
        """Persist successful completion."""

    @abstractmethod
    def mark_failed(self, migration: Migration, error: str) -> None:
        """Persist failed completion."""
