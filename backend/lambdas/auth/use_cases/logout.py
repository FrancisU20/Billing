from __future__ import annotations

"""Logout use case."""

from lambdas.auth.domain.commands import LogoutCommand
from lambdas.auth.domain.repositories.i_auth_provider import IAuthProvider


class LogoutUseCase:
    def __init__(self, auth_provider: IAuthProvider) -> None:
        self._auth_provider = auth_provider

    def execute(self, command: LogoutCommand) -> None:
        self._auth_provider.logout(command)
