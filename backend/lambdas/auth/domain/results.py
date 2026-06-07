from __future__ import annotations

"""Auth result value objects."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AuthTokens:
    id_token: str
    access_token: str
    expires_in: int
    token_type: str
    refresh_token: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id_token": self.id_token,
            "access_token": self.access_token,
            "expires_in": self.expires_in,
            "token_type": self.token_type,
        }
        if self.refresh_token:
            data["refresh_token"] = self.refresh_token
        return data


@dataclass(frozen=True)
class AuthChallenge:
    challenge_name: str
    session: str
    parameters: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "challenge_name": self.challenge_name,
            "session": self.session,
            "parameters": self.parameters,
        }


AuthOutcome = AuthTokens | AuthChallenge
