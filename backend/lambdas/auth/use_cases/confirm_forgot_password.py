from __future__ import annotations

"""Confirm forgot password use case."""

from lambdas.auth.domain.commands import ConfirmForgotPasswordCommand
from lambdas.auth.domain.repositories.i_auth_provider import IAuthProvider


class ConfirmForgotPasswordUseCase:
    def __init__(self, auth_provider: IAuthProvider) -> None:
        self._auth_provider = auth_provider

    def execute(self, command: ConfirmForgotPasswordCommand) -> None:
        self._auth_provider.confirm_forgot_password(command)
