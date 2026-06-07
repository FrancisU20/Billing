from __future__ import annotations

"""Refresh token use case."""

from lambdas.auth.domain.commands import RefreshCommand
from lambdas.auth.domain.repositories.i_auth_provider import IAuthProvider
from lambdas.auth.domain.results import AuthOutcome


class RefreshUseCase:
    def __init__(self, auth_provider: IAuthProvider) -> None:
        self._auth_provider = auth_provider

    def execute(self, command: RefreshCommand) -> AuthOutcome:
        return self._auth_provider.refresh(command)
