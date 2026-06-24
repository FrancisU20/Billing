from __future__ import annotations

"""
Auth Lambda — AWS entry point.

Routes:
    POST /auth/login            login with Cognito USER_SRP_AUTH
    POST /auth/refresh          refresh Cognito tokens
    POST /auth/logout           global logout with access_token from the body
    POST /auth/challenge        respond to Cognito auth challenges
    POST /auth/forgot-password  request a password reset code by email
    POST /auth/reset-password   complete a password reset with the emailed code
"""

from lambdas._base.handler import public_lambda_handler
from lambdas._base.parser import Request, parse
from lambdas._base.response import ApiResponse
from lambdas.auth.domain.commands import (
    ConfirmForgotPasswordCommand,
    ForgotPasswordCommand,
    LoginCommand,
    LogoutCommand,
    RefreshCommand,
    RespondChallengeCommand,
)
from lambdas.auth.domain.repositories.i_auth_provider import IAuthProvider
from lambdas.auth.infra.cognito_auth_provider import CognitoAuthProvider
from lambdas.auth.infra.password_reset_repository import DynamoPasswordResetRepository
from lambdas.auth.schemas import (
    ChallengeRequest,
    ConfirmForgotPasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
)
from lambdas.auth.use_cases.confirm_forgot_password import ConfirmForgotPasswordUseCase
from lambdas.auth.use_cases.forgot_password import ForgotPasswordUseCase
from lambdas.auth.use_cases.login import LoginUseCase
from lambdas.auth.use_cases.logout import LogoutUseCase
from lambdas.auth.use_cases.refresh import RefreshUseCase
from lambdas.auth.use_cases.respond_challenge import RespondChallengeUseCase
from shared.config import env
from shared.db.client import get_table
from shared.domain.events.publisher import EventPublisher
from shared.errors import NotFoundError

_provider_instance = CognitoAuthProvider()
_password_reset_repo: DynamoPasswordResetRepository | None = None
_event_publisher = EventPublisher(queue_url=env("EMAIL_NOTIFICATIONS_QUEUE_URL", ""))


def _provider() -> IAuthProvider:
    return _provider_instance


def _reset_repository() -> DynamoPasswordResetRepository:
    global _password_reset_repo
    if _password_reset_repo is None:
        _password_reset_repo = DynamoPasswordResetRepository(get_table("PASSWORD_RESETS_TABLE"))
    return _password_reset_repo


@public_lambda_handler
def _login(request: Request, context) -> dict:
    body = parse(LoginRequest, request.body)
    result = LoginUseCase(_provider()).execute(
        LoginCommand(username=body.username, password=body.password)
    )
    return ApiResponse.ok(result.to_dict(), request.request_id)


@public_lambda_handler
def _refresh(request: Request, context) -> dict:
    body = parse(RefreshRequest, request.body)
    result = RefreshUseCase(_provider()).execute(RefreshCommand(refresh_token=body.refresh_token))
    return ApiResponse.ok(result.to_dict(), request.request_id)


@public_lambda_handler
def _logout(request: Request, context) -> dict:
    body = parse(LogoutRequest, request.body)
    LogoutUseCase(_provider()).execute(LogoutCommand(access_token=body.access_token))
    return ApiResponse.no_content(request.request_id)


@public_lambda_handler
def _challenge(request: Request, context) -> dict:
    body = parse(ChallengeRequest, request.body)
    result = RespondChallengeUseCase(_provider()).execute(
        RespondChallengeCommand(
            session=body.session,
            challenge_name=body.challenge_name,
            responses=body.responses,
        )
    )
    return ApiResponse.ok(result.to_dict(), request.request_id)


@public_lambda_handler
def _forgot_password(request: Request, context) -> dict:
    body = parse(ForgotPasswordRequest, request.body)
    ForgotPasswordUseCase(_provider(), _reset_repository(), _event_publisher).execute(
        ForgotPasswordCommand(username=body.username)
    )
    return ApiResponse.ok(
        {"message": "Si el correo está registrado, te enviamos un código de recuperación."},
        request.request_id,
    )


@public_lambda_handler
def _reset_password(request: Request, context) -> dict:
    body = parse(ConfirmForgotPasswordRequest, request.body)
    ConfirmForgotPasswordUseCase(_provider(), _reset_repository()).execute(
        ConfirmForgotPasswordCommand(
            username=body.username,
            confirmation_code=body.confirmation_code,
            new_password=body.new_password,
        )
    )
    return ApiResponse.no_content(request.request_id)


def handler(event: dict, context) -> dict:
    ctx = event.get("requestContext", {})
    http = ctx.get("http", {})
    method = http.get("method", "")
    path = http.get("path", event.get("rawPath", ""))

    if method == "POST":
        if path == "/auth/login":
            return _login(event, context)
        if path == "/auth/refresh":
            return _refresh(event, context)
        if path == "/auth/logout":
            return _logout(event, context)
        if path == "/auth/challenge":
            return _challenge(event, context)
        if path == "/auth/forgot-password":
            return _forgot_password(event, context)
        if path == "/auth/reset-password":
            return _reset_password(event, context)

    return ApiResponse.error(NotFoundError(), ctx.get("requestId", "local"))
