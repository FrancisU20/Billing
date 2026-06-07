from __future__ import annotations

"""Login use case."""

from lambdas.auth.domain.commands import LoginCommand
from lambdas.auth.domain.repositories.i_auth_provider import IAuthProvider
from lambdas.auth.domain.results import AuthOutcome


class LoginUseCase:
    def __init__(self, auth_provider: IAuthProvider) -> None:
        self._auth_provider = auth_provider

    def execute(self, command: LoginCommand) -> AuthOutcome:
        return self._auth_provider.login(command)
