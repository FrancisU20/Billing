from __future__ import annotations

from abc import ABC, abstractmethod


class IIdentityProvider(ABC):
    @abstractmethod
    def email_exists(self, email: str) -> bool:
        """Return True if a Cognito user already exists for this email."""
