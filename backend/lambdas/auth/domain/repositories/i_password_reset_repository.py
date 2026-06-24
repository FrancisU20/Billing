from __future__ import annotations

from abc import ABC, abstractmethod

from lambdas.auth.domain.password_reset import PasswordReset


class IPasswordResetRepository(ABC):
    @abstractmethod
    def save(self, reset: PasswordReset) -> None:
        """Create or replace the active reset code for a username."""

    @abstractmethod
    def get_by_username(self, username: str) -> PasswordReset | None:
        """Return the reset request for a username, if any."""

    @abstractmethod
    def save_attempts(self, reset: PasswordReset) -> None:
        """Persist failed confirmation attempts."""

    @abstractmethod
    def mark_used(self, reset: PasswordReset) -> None:
        """Mark a reset code as consumed."""
