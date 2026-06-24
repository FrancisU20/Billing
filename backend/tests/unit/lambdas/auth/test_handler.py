from __future__ import annotations

import importlib
import os
import sys
import unittest

from lambdas.auth.domain.commands import (
    LoginCommand,
    LogoutCommand,
    RefreshCommand,
    RespondChallengeCommand,
)
from lambdas.auth.domain.password_reset import PasswordReset
from lambdas.auth.domain.repositories.i_auth_provider import IAuthProvider
from lambdas.auth.domain.results import AuthChallenge, AuthOutcome, AuthTokens
from tests.unit.support import LambdaContext, api_event, configure_unit_environment, decode_response


class FakeAuthProvider(IAuthProvider):
    def __init__(self) -> None:
        self.login_calls: list[LoginCommand] = []
        self.refresh_calls: list[RefreshCommand] = []
        self.logout_calls: list[LogoutCommand] = []
        self.challenge_calls: list[RespondChallengeCommand] = []
        self.user_exists_calls: list[str] = []
        self.set_password_calls: list[dict] = []
        self.user_exists_result = True
        self.login_result: AuthOutcome = AuthTokens(
            id_token="id-token",
            access_token="access-token",
            refresh_token="refresh-token",
            expires_in=3600,
            token_type="Bearer",
        )
        self.refresh_result: AuthOutcome = AuthTokens(
            id_token="new-id-token",
            access_token="new-access-token",
            expires_in=3600,
            token_type="Bearer",
        )
        self.challenge_result: AuthOutcome = AuthTokens(
            id_token="challenge-id-token",
            access_token="challenge-access-token",
            refresh_token="challenge-refresh-token",
            expires_in=3600,
            token_type="Bearer",
        )

    def login(self, command: LoginCommand) -> AuthOutcome:
        self.login_calls.append(command)
        return self.login_result

    def refresh(self, command: RefreshCommand) -> AuthOutcome:
        self.refresh_calls.append(command)
        return self.refresh_result

    def logout(self, command: LogoutCommand) -> None:
        self.logout_calls.append(command)

    def respond_to_challenge(self, command: RespondChallengeCommand) -> AuthOutcome:
        self.challenge_calls.append(command)
        return self.challenge_result

    def user_exists(self, username: str) -> bool:
        self.user_exists_calls.append(username)
        return self.user_exists_result

    def set_permanent_password(self, *, username: str, password: str) -> None:
        self.set_password_calls.append({"username": username, "password": password})


class FakePasswordResetRepository:
    def __init__(self) -> None:
        self.saved: list[PasswordReset] = []
        self.attempts_saved: list[PasswordReset] = []
        self.used: list[PasswordReset] = []
        self.current_reset = PasswordReset.create(username="owner@codelabs.com", code="123456")

    def save(self, reset: PasswordReset) -> None:
        self.saved.append(reset)

    def get_by_username(self, username: str) -> PasswordReset | None:
        if self.current_reset and self.current_reset.username == username:
            return self.current_reset
        return None

    def save_attempts(self, reset: PasswordReset) -> None:
        self.attempts_saved.append(reset)

    def mark_used(self, reset: PasswordReset) -> None:
        reset.mark_used()
        self.used.append(reset)


class FakeEventPublisher:
    def __init__(self) -> None:
        self.events: list[object] = []

    def publish(self, event: object) -> None:
        self.events.append(event)


def _load_handler_module():
    configure_unit_environment()
    os.environ["COGNITO_USER_POOL_ID"] = "sa-east-1_unit"
    os.environ["COGNITO_WEB_CLIENT_ID"] = "client-id"
    sys.modules.pop("lambdas.auth.handler", None)
    return importlib.import_module("lambdas.auth.handler")


class AuthHandlerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.handler = _load_handler_module()
        self.provider = FakeAuthProvider()
        self.reset_repo = FakePasswordResetRepository()
        self.publisher = FakeEventPublisher()
        self.handler._provider = lambda: self.provider
        self.handler._reset_repository = lambda: self.reset_repo
        self.handler._event_publisher = self.publisher
        self.context = LambdaContext()

    def test_login_returns_tokens_and_normalizes_username(self) -> None:
        response = self.handler.handler(
            api_event(
                method="POST",
                path="/auth/login",
                body={"username": "OWNER@CODELABS.COM ", "password": "secret"},
                claims={},
            ),
            self.context,
        )

        body = decode_response(response)
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(body["data"]["id_token"], "id-token")
        self.assertEqual(body["data"]["refresh_token"], "refresh-token")
        self.assertEqual(self.provider.login_calls[0].username, "owner@codelabs.com")

    def test_login_can_return_new_password_challenge(self) -> None:
        self.provider.login_result = AuthChallenge(
            challenge_name="NEW_PASSWORD_REQUIRED",
            session="challenge-session",
            parameters={"username": "owner@example.com", "requiredAttributes": "[]"},
        )

        response = self.handler.handler(
            api_event(
                method="POST",
                path="/auth/login",
                body={"username": "owner@example.com", "password": "temporary"},
                claims={},
            ),
            self.context,
        )

        body = decode_response(response)
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(body["data"]["challenge_name"], "NEW_PASSWORD_REQUIRED")
        self.assertEqual(body["data"]["session"], "challenge-session")
        self.assertEqual(body["data"]["parameters"]["username"], "owner@example.com")

    def test_refresh_uses_refresh_token_auth(self) -> None:
        response = self.handler.handler(
            api_event(
                method="POST",
                path="/auth/refresh",
                body={"refresh_token": "refresh-token"},
                claims={},
            ),
            self.context,
        )

        body = decode_response(response)
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(body["data"]["access_token"], "new-access-token")
        self.assertEqual(body["data"].get("refresh_token"), None)
        self.assertEqual(self.provider.refresh_calls[0].refresh_token, "refresh-token")

    def test_logout_uses_access_token_from_body(self) -> None:
        response = self.handler.handler(
            api_event(
                method="POST",
                path="/auth/logout",
                body={"access_token": "access-token"},
                claims={},
            ),
            self.context,
        )

        body = decode_response(response)
        self.assertEqual(response["statusCode"], 204)
        self.assertTrue(body["success"])
        self.assertEqual(self.provider.logout_calls[0].access_token, "access-token")

    def test_challenge_forwards_session_name_and_responses(self) -> None:
        response = self.handler.handler(
            api_event(
                method="POST",
                path="/auth/challenge",
                body={
                    "session": "session-token",
                    "challenge_name": "new_password_required",
                    "responses": {
                        "USERNAME": "owner@example.com",
                        "NEW_PASSWORD": "PermanentPass123!",
                    },
                },
                claims={},
            ),
            self.context,
        )

        body = decode_response(response)
        call = self.provider.challenge_calls[0]
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(body["data"]["id_token"], "challenge-id-token")
        self.assertEqual(call.session, "session-token")
        self.assertEqual(call.challenge_name, "NEW_PASSWORD_REQUIRED")
        self.assertEqual(call.responses["NEW_PASSWORD"], "PermanentPass123!")

    def test_forgot_password_normalizes_username_and_returns_generic_message(self) -> None:
        response = self.handler.handler(
            api_event(
                method="POST",
                path="/auth/forgot-password",
                body={"username": "OWNER@CODELABS.COM "},
                claims={},
            ),
            self.context,
        )

        body = decode_response(response)
        self.assertEqual(response["statusCode"], 200)
        self.assertIn("código de recuperación", body["data"]["message"])
        self.assertEqual(self.provider.user_exists_calls[0], "owner@codelabs.com")
        self.assertEqual(self.reset_repo.saved[0].username, "owner@codelabs.com")
        self.assertEqual(self.publisher.events[0].email, "owner@codelabs.com")
        self.assertEqual(len(self.publisher.events[0].code), 6)

    def test_forgot_password_does_not_send_email_when_user_does_not_exist(self) -> None:
        self.provider.user_exists_result = False

        response = self.handler.handler(
            api_event(
                method="POST",
                path="/auth/forgot-password",
                body={"username": "missing@codelabs.com"},
                claims={},
            ),
            self.context,
        )

        body = decode_response(response)
        self.assertEqual(response["statusCode"], 200)
        self.assertIn("código de recuperación", body["data"]["message"])
        self.assertEqual(self.reset_repo.saved, [])
        self.assertEqual(self.publisher.events, [])

    def test_reset_password_returns_204(self) -> None:
        response = self.handler.handler(
            api_event(
                method="POST",
                path="/auth/reset-password",
                body={
                    "username": "owner@codelabs.com",
                    "confirmation_code": "123456",
                    "new_password": "NewPermanentPass123!",
                },
                claims={},
            ),
            self.context,
        )

        body = decode_response(response)
        self.assertEqual(response["statusCode"], 204)
        self.assertTrue(body["success"])
        call = self.provider.set_password_calls[0]
        self.assertEqual(call["username"], "owner@codelabs.com")
        self.assertEqual(call["password"], "NewPermanentPass123!")
        self.assertEqual(len(self.reset_repo.used), 1)

    def test_invalid_login_body_returns_400(self) -> None:
        response = self.handler.handler(
            api_event(
                method="POST",
                path="/auth/login",
                body={"username": "a"},
                claims={},
            ),
            self.context,
        )

        body = decode_response(response)
        self.assertEqual(response["statusCode"], 400)
        self.assertEqual(body["error"]["code"], "VALIDATION_ERROR")

    def test_unknown_route_returns_404(self) -> None:
        response = self.handler.handler(
            api_event(method="GET", path="/auth/login", claims={}),
            self.context,
        )
        self.assertEqual(response["statusCode"], 404)


if __name__ == "__main__":
    unittest.main()
