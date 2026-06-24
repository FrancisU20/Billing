from __future__ import annotations

"""Confirm forgot password use case."""

from lambdas.auth.domain.commands import ConfirmForgotPasswordCommand
from lambdas.auth.domain.errors import InvalidChallengeResponseError
from lambdas.auth.domain.repositories.i_auth_provider import IAuthProvider
from lambdas.auth.domain.repositories.i_password_reset_repository import IPasswordResetRepository


class ConfirmForgotPasswordUseCase:
    def __init__(
        self,
        auth_provider: IAuthProvider,
        reset_repository: IPasswordResetRepository,
    ) -> None:
        self._auth_provider = auth_provider
        self._reset_repository = reset_repository

    def execute(self, command: ConfirmForgotPasswordCommand) -> None:
        reset = self._reset_repository.get_by_username(command.username)
        if reset is None:
            raise InvalidChallengeResponseError(detail="PasswordResetNotFound")

        reset.ensure_active()
        if not reset.verify(command.confirmation_code):
            try:
                reset.register_failed_attempt()
            finally:
                self._reset_repository.save_attempts(reset)

        self._auth_provider.set_permanent_password(
            username=command.username,
            password=command.new_password,
        )
        self._reset_repository.mark_used(reset)
