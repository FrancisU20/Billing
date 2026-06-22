from __future__ import annotations

"""Port implemented by the identity provider adapter."""

from abc import ABC, abstractmethod

from lambdas.auth.domain.commands import (
    ConfirmForgotPasswordCommand,
    ForgotPasswordCommand,
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
    def forgot_password(self, command: ForgotPasswordCommand) -> None:
        """Request a password reset code by email.

        Never raises for an unknown username — always succeeds from the
        caller's perspective to avoid leaking account existence.
        """

    @abstractmethod
    def confirm_forgot_password(self, command: ConfirmForgotPasswordCommand) -> None:
        """Complete a password reset with the emailed confirmation code."""
