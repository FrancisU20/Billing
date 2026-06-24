from __future__ import annotations

"""Forgot password use case."""

from lambdas.auth.domain.commands import ForgotPasswordCommand
from lambdas.auth.domain.events import PasswordResetRequestedEvent
from lambdas.auth.domain.password_reset import PasswordReset, generate_reset_code
from lambdas.auth.domain.repositories.i_auth_provider import IAuthProvider
from lambdas.auth.domain.repositories.i_password_reset_repository import IPasswordResetRepository
from shared.domain.events.publisher import EventPublisher


class ForgotPasswordUseCase:
    def __init__(
        self,
        auth_provider: IAuthProvider,
        reset_repository: IPasswordResetRepository,
        event_publisher: EventPublisher,
    ) -> None:
        self._auth_provider = auth_provider
        self._reset_repository = reset_repository
        self._event_publisher = event_publisher

    def execute(self, command: ForgotPasswordCommand) -> None:
        if not self._auth_provider.user_exists(command.username):
            return

        code = generate_reset_code()
        reset = PasswordReset.create(username=command.username, code=code)
        self._reset_repository.save(reset)
        self._event_publisher.publish(
            PasswordResetRequestedEvent(
                email=command.username,
                code=code,
                expires_at=reset.expires_at,
            )
        )
