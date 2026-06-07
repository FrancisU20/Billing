from __future__ import annotations

"""
Auth Lambda — AWS entry point.

Routes:
    POST /auth/login      login with Cognito USER_SRP_AUTH
    POST /auth/refresh    refresh Cognito tokens
    POST /auth/logout     global logout with access_token from the body
    POST /auth/challenge  respond to Cognito auth challenges
"""

from lambdas._base.handler import public_lambda_handler
from lambdas._base.parser import Request, parse
from lambdas._base.response import ApiResponse
from lambdas.auth.domain.commands import (
    LoginCommand,
    LogoutCommand,
    RefreshCommand,
    RespondChallengeCommand,
)
from lambdas.auth.domain.repositories.i_auth_provider import IAuthProvider
from lambdas.auth.infra.cognito_auth_provider import CognitoAuthProvider
from lambdas.auth.schemas import ChallengeRequest, LoginRequest, LogoutRequest, RefreshRequest
from lambdas.auth.use_cases.login import LoginUseCase
from lambdas.auth.use_cases.logout import LogoutUseCase
from lambdas.auth.use_cases.refresh import RefreshUseCase
from lambdas.auth.use_cases.respond_challenge import RespondChallengeUseCase
from shared.errors import NotFoundError

_provider_instance = CognitoAuthProvider()


def _provider() -> IAuthProvider:
    return _provider_instance


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

    return ApiResponse.error(NotFoundError(), ctx.get("requestId", "local"))
