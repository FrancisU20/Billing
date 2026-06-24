from __future__ import annotations

"""Port implemented by the identity provider adapter."""

from abc import ABC, abstractmethod

from lambdas.auth.domain.commands import (
    LoginCommand,
    LogoutCommand,
    RefreshCommand,
    RespondChallengeCommand,
)
from lambdas.auth.domain.results import AuthOutcome


class IAuthProvider(ABC):
    @abstractmethod
    def login(self, command: LoginCommand) -> AuthOutcome:
        """Authenticate with SRP and return tokens or the next challenge."""

    @abstractmethod
    def refresh(self, command: RefreshCommand) -> AuthOutcome:
        """Refresh tokens with a refresh token."""

    @abstractmethod
    def logout(self, command: LogoutCommand) -> None:
        """Invalidate all tokens associated with the given access token."""

    @abstractmethod
    def respond_to_challenge(self, command: RespondChallengeCommand) -> AuthOutcome:
        """Continue a Cognito auth challenge."""

    @abstractmethod
    def user_exists(self, username: str) -> bool:
        """Return whether the user exists without leaking that to public handlers."""

    @abstractmethod
    def set_permanent_password(self, *, username: str, password: str) -> None:
        """Set a definitive password after our own reset code was verified."""
