from __future__ import annotations

"""Respond to auth challenge use case."""

from lambdas.auth.domain.commands import RespondChallengeCommand
from lambdas.auth.domain.repositories.i_auth_provider import IAuthProvider
from lambdas.auth.domain.results import AuthOutcome


class RespondChallengeUseCase:
    def __init__(self, auth_provider: IAuthProvider) -> None:
        self._auth_provider = auth_provider

    def execute(self, command: RespondChallengeCommand) -> AuthOutcome:
        return self._auth_provider.respond_to_challenge(command)
