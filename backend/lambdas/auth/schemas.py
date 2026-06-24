from __future__ import annotations

"""Pydantic schemas for auth HTTP requests."""

from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=1024)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip().lower()


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1, max_length=8192)


class LogoutRequest(BaseModel):
    access_token: str = Field(min_length=1, max_length=8192)


class ForgotPasswordRequest(BaseModel):
    username: str = Field(min_length=3, max_length=320)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip().lower()


class ConfirmForgotPasswordRequest(BaseModel):
    username: str = Field(min_length=3, max_length=320)
    confirmation_code: str = Field(min_length=6, max_length=6)
    new_password: str = Field(min_length=12, max_length=1024)

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        return value.strip().lower()


class ChallengeRequest(BaseModel):
    session: str = Field(min_length=1, max_length=8192)
    challenge_name: str = Field(min_length=1, max_length=128)
    responses: dict[str, str] = Field(min_length=1)

    @field_validator("challenge_name")
    @classmethod
    def normalize_challenge_name(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("responses")
    @classmethod
    def validate_responses(cls, value: dict[str, str]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for key, raw in value.items():
            clean_key = key.strip()
            if not clean_key:
                raise ValueError("responses no puede contener llaves vacías")
            if not isinstance(raw, str) or raw == "":
                raise ValueError("responses debe contener valores string no vacíos")
            normalized[clean_key] = raw
        return normalized
