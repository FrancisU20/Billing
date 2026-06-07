from __future__ import annotations

"""Commands for auth use cases."""

from dataclasses import dataclass


@dataclass(frozen=True)
class LoginCommand:
    username: str
    password: str


@dataclass(frozen=True)
class RefreshCommand:
    refresh_token: str


@dataclass(frozen=True)
class LogoutCommand:
    access_token: str


@dataclass(frozen=True)
class RespondChallengeCommand:
    challenge_name: str
    session: str
    responses: dict[str, str]
