from __future__ import annotations

"""Forgot password use case."""

from lambdas.auth.domain.commands import ForgotPasswordCommand
from lambdas.auth.domain.repositories.i_auth_provider import IAuthProvider


class ForgotPasswordUseCase:
    def __init__(self, auth_provider: IAuthProvider) -> None:
        self._auth_provider = auth_provider

    def execute(self, command: ForgotPasswordCommand) -> None:
        self._auth_provider.forgot_password(command)
