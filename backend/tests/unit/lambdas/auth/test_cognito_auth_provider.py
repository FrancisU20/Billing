from __future__ import annotations

import unittest
from unittest.mock import patch

from botocore.exceptions import ClientError

from lambdas.auth.domain.commands import (
    LoginCommand,
    LogoutCommand,
    RefreshCommand,
    RespondChallengeCommand,
)
from lambdas.auth.domain.errors import InvalidChallengeResponseError
from lambdas.auth.domain.results import AuthChallenge, AuthTokens
from lambdas.auth.infra.cognito_auth_provider import CognitoAuthProvider
from shared.errors import ExternalServiceError, InvalidCredentialsError


def _client_error(code: str) -> ClientError:
    return ClientError(
        {"Error": {"Code": code, "Message": code}},
        "UnitTestOperation",
    )


class FakeSrpSession:
    def __init__(self, *, user_pool_id: str, username: str, password: str) -> None:
        self.user_pool_id = user_pool_id
        self.username = username
        self.password = password
        self.srp_a = "srp-a"

    def challenge_responses(self, challenge: dict[str, str]) -> dict[str, str]:
        return {
            "USERNAME": challenge["USER_ID_FOR_SRP"],
            "PASSWORD_CLAIM_SECRET_BLOCK": challenge["SECRET_BLOCK"],
            "PASSWORD_CLAIM_SIGNATURE": "signature",
            "TIMESTAMP": "Mon Jan 1 00:00:00 UTC 2026",
        }


class FakeCognitoClient:
    def __init__(
        self,
        *,
        auth_response: dict | Exception | None = None,
        challenge_response: dict | Exception | None = None,
        refresh_response: dict | Exception | None = None,
        admin_get_user_response: dict | Exception | None = None,
        admin_set_user_password_response: dict | Exception | None = None,
    ) -> None:
        self.auth_response = auth_response or {
            "ChallengeName": "PASSWORD_VERIFIER",
            "ChallengeParameters": {
                "USER_ID_FOR_SRP": "owner@example.com",
                "SALT": "abcd",
                "SRP_B": "1234",
                "SECRET_BLOCK": "secret-block",
            },
        }
        self.challenge_response = challenge_response or {
            "AuthenticationResult": {
                "IdToken": "id-token",
                "AccessToken": "access-token",
                "RefreshToken": "refresh-token",
                "ExpiresIn": 3600,
                "TokenType": "Bearer",
            }
        }
        self.refresh_response = refresh_response or {
            "AuthenticationResult": {
                "IdToken": "new-id-token",
                "AccessToken": "new-access-token",
                "ExpiresIn": 3600,
                "TokenType": "Bearer",
            }
        }
        self.admin_get_user_response = admin_get_user_response or {"Username": "owner@example.com"}
        self.admin_set_user_password_response = admin_set_user_password_response
        self.initiate_auth_calls: list[dict] = []
        self.respond_to_auth_challenge_calls: list[dict] = []
        self.global_sign_out_calls: list[dict] = []
        self.admin_get_user_calls: list[dict] = []
        self.admin_set_user_password_calls: list[dict] = []

    def initiate_auth(self, **kwargs):
        self.initiate_auth_calls.append(kwargs)
        if kwargs["AuthFlow"] == "REFRESH_TOKEN_AUTH":
            if isinstance(self.refresh_response, Exception):
                raise self.refresh_response
            return self.refresh_response
        if isinstance(self.auth_response, Exception):
            raise self.auth_response
        return self.auth_response

    def respond_to_auth_challenge(self, **kwargs):
        self.respond_to_auth_challenge_calls.append(kwargs)
        if isinstance(self.challenge_response, Exception):
            raise self.challenge_response
        return self.challenge_response

    def global_sign_out(self, **kwargs):
        self.global_sign_out_calls.append(kwargs)

    def admin_get_user(self, **kwargs):
        self.admin_get_user_calls.append(kwargs)
        if isinstance(self.admin_get_user_response, Exception):
            raise self.admin_get_user_response
        return self.admin_get_user_response

    def admin_set_user_password(self, **kwargs):
        self.admin_set_user_password_calls.append(kwargs)
        if isinstance(self.admin_set_user_password_response, Exception):
            raise self.admin_set_user_password_response
        return self.admin_set_user_password_response or {}


class CognitoAuthProviderTests(unittest.TestCase):
    def test_sanitize_challenge_parameters_removes_srp_secrets(self) -> None:
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)

        result = provider._sanitize_challenge_parameters(
            {
                "USER_ID_FOR_SRP": "owner@example.com",
                "SALT": "salt",
                "SRP_B": "srp-b",
                "SECRET_BLOCK": "secret",
                "requiredAttributes": "[]",
            }
        )

        self.assertEqual(result["username"], "owner@example.com")
        self.assertEqual(result["USER_ID_FOR_SRP"], "owner@example.com")
        self.assertEqual(result["requiredAttributes"], "[]")
        self.assertNotIn("SALT", result)
        self.assertNotIn("SRP_B", result)
        self.assertNotIn("SECRET_BLOCK", result)

    def test_login_uses_user_srp_auth_and_password_verifier(self) -> None:
        idp = FakeCognitoClient()
        provider = CognitoAuthProvider(
            idp=idp, user_pool_id="sa-east-1_unit", client_id="client-id"
        )

        with patch(
            "lambdas.auth.infra.cognito_auth_provider.CognitoSrpSession",
            FakeSrpSession,
        ):
            result = provider.login(LoginCommand(username="owner@example.com", password="secret"))

        self.assertIsInstance(result, AuthTokens)
        self.assertEqual(result.id_token, "id-token")
        self.assertEqual(idp.initiate_auth_calls[0]["AuthFlow"], "USER_SRP_AUTH")
        self.assertEqual(
            idp.initiate_auth_calls[0]["AuthParameters"],
            {"USERNAME": "owner@example.com", "SRP_A": "srp-a"},
        )
        verifier_call = idp.respond_to_auth_challenge_calls[0]
        self.assertEqual(verifier_call["ClientId"], "client-id")
        self.assertEqual(verifier_call["ChallengeName"], "PASSWORD_VERIFIER")
        self.assertEqual(
            verifier_call["ChallengeResponses"]["PASSWORD_CLAIM_SIGNATURE"], "signature"
        )

    def test_login_returns_pending_challenge_when_not_password_verifier(self) -> None:
        idp = FakeCognitoClient(
            auth_response={
                "ChallengeName": "NEW_PASSWORD_REQUIRED",
                "Session": "session-token",
                "ChallengeParameters": {
                    "USER_ID_FOR_SRP": "owner@example.com",
                    "requiredAttributes": "[]",
                },
            }
        )
        provider = CognitoAuthProvider(
            idp=idp, user_pool_id="sa-east-1_unit", client_id="client-id"
        )

        with patch(
            "lambdas.auth.infra.cognito_auth_provider.CognitoSrpSession",
            FakeSrpSession,
        ):
            result = provider.login(
                LoginCommand(username="owner@example.com", password="temporary")
            )

        self.assertIsInstance(result, AuthChallenge)
        self.assertEqual(result.challenge_name, "NEW_PASSWORD_REQUIRED")
        self.assertEqual(result.session, "session-token")
        self.assertEqual(result.parameters["username"], "owner@example.com")
        self.assertEqual(idp.respond_to_auth_challenge_calls, [])

    def test_login_carries_user_id_for_srp_into_chained_challenge(self) -> None:
        idp = FakeCognitoClient(
            auth_response={
                "ChallengeName": "PASSWORD_VERIFIER",
                "ChallengeParameters": {
                    "USER_ID_FOR_SRP": "11111111-2222-3333-4444-555555555555",
                    "SALT": "abcd",
                    "SRP_B": "1234",
                    "SECRET_BLOCK": "secret-block",
                },
            },
            challenge_response={
                "ChallengeName": "NEW_PASSWORD_REQUIRED",
                "Session": "session-token",
                "ChallengeParameters": {"requiredAttributes": "[]"},
            },
        )
        provider = CognitoAuthProvider(
            idp=idp, user_pool_id="sa-east-1_unit", client_id="client-id"
        )

        with patch(
            "lambdas.auth.infra.cognito_auth_provider.CognitoSrpSession",
            FakeSrpSession,
        ):
            result = provider.login(
                LoginCommand(username="owner@example.com", password="temporary")
            )

        self.assertIsInstance(result, AuthChallenge)
        self.assertEqual(result.challenge_name, "NEW_PASSWORD_REQUIRED")
        # USERNAME para RespondToAuthChallenge debe ser el USER_ID_FOR_SRP del
        # paso SRP inicial (sub interno), no el alias de email usado para login.
        self.assertEqual(result.parameters["username"], "11111111-2222-3333-4444-555555555555")

    def test_refresh_uses_refresh_token_auth(self) -> None:
        idp = FakeCognitoClient()
        provider = CognitoAuthProvider(
            idp=idp, user_pool_id="sa-east-1_unit", client_id="client-id"
        )

        result = provider.refresh(RefreshCommand(refresh_token="refresh-token"))

        self.assertIsInstance(result, AuthTokens)
        self.assertEqual(result.access_token, "new-access-token")
        self.assertEqual(idp.initiate_auth_calls[0]["AuthFlow"], "REFRESH_TOKEN_AUTH")
        self.assertEqual(
            idp.initiate_auth_calls[0]["AuthParameters"],
            {"REFRESH_TOKEN": "refresh-token"},
        )

    def test_logout_uses_global_sign_out(self) -> None:
        idp = FakeCognitoClient()
        provider = CognitoAuthProvider(
            idp=idp, user_pool_id="sa-east-1_unit", client_id="client-id"
        )

        provider.logout(LogoutCommand(access_token="access-token"))

        self.assertEqual(idp.global_sign_out_calls[0], {"AccessToken": "access-token"})

    def test_respond_to_new_password_required_challenge(self) -> None:
        idp = FakeCognitoClient()
        provider = CognitoAuthProvider(
            idp=idp, user_pool_id="sa-east-1_unit", client_id="client-id"
        )

        result = provider.respond_to_challenge(
            RespondChallengeCommand(
                challenge_name="NEW_PASSWORD_REQUIRED",
                session="session-token",
                responses={
                    "USERNAME": "owner@example.com",
                    "NEW_PASSWORD": "PermanentPass123!",
                },
            )
        )

        self.assertIsInstance(result, AuthTokens)
        self.assertEqual(idp.respond_to_auth_challenge_calls[0]["ClientId"], "client-id")
        self.assertEqual(
            idp.respond_to_auth_challenge_calls[0]["ChallengeName"],
            "NEW_PASSWORD_REQUIRED",
        )
        self.assertEqual(idp.respond_to_auth_challenge_calls[0]["Session"], "session-token")
        self.assertEqual(
            idp.respond_to_auth_challenge_calls[0]["ChallengeResponses"]["NEW_PASSWORD"],
            "PermanentPass123!",
        )

    def test_incomplete_authentication_result_is_external_service_error(self) -> None:
        provider = CognitoAuthProvider.__new__(CognitoAuthProvider)

        with self.assertRaises(ExternalServiceError):
            provider._outcome_from_response(
                {
                    "AuthenticationResult": {
                        "AccessToken": "access-token",
                        "ExpiresIn": 3600,
                        "TokenType": "Bearer",
                    }
                }
            )

    def test_maps_cognito_auth_errors(self) -> None:
        for code in ("NotAuthorizedException", "UserNotFoundException"):
            with self.subTest(code=code):
                idp = FakeCognitoClient(refresh_response=_client_error(code))
                provider = CognitoAuthProvider(
                    idp=idp,
                    user_pool_id="sa-east-1_unit",
                    client_id="client-id",
                )
                with self.assertRaises(InvalidCredentialsError):
                    provider.refresh(RefreshCommand(refresh_token="refresh-token"))

    def test_maps_cognito_challenge_errors(self) -> None:
        for code in ("CodeMismatchException", "ExpiredCodeException", "InvalidPasswordException"):
            with self.subTest(code=code):
                idp = FakeCognitoClient(challenge_response=_client_error(code))
                provider = CognitoAuthProvider(
                    idp=idp,
                    user_pool_id="sa-east-1_unit",
                    client_id="client-id",
                )
                with self.assertRaises(InvalidChallengeResponseError):
                    provider.respond_to_challenge(
                        RespondChallengeCommand(
                            challenge_name="NEW_PASSWORD_REQUIRED",
                            session="session-token",
                            responses={"USERNAME": "owner@example.com"},
                        )
                    )

    def test_user_exists_calls_admin_get_user(self) -> None:
        idp = FakeCognitoClient()
        provider = CognitoAuthProvider(
            idp=idp, user_pool_id="sa-east-1_unit", client_id="client-id"
        )

        result = provider.user_exists("owner@example.com")

        self.assertTrue(result)
        self.assertEqual(
            idp.admin_get_user_calls[0],
            {"UserPoolId": "sa-east-1_unit", "Username": "owner@example.com"},
        )

    def test_user_exists_returns_false_for_user_not_found(self) -> None:
        idp = FakeCognitoClient(admin_get_user_response=_client_error("UserNotFoundException"))
        provider = CognitoAuthProvider(
            idp=idp, user_pool_id="sa-east-1_unit", client_id="client-id"
        )

        self.assertFalse(provider.user_exists("missing@example.com"))

    def test_user_exists_propagates_other_errors(self) -> None:
        idp = FakeCognitoClient(admin_get_user_response=_client_error("LimitExceededException"))
        provider = CognitoAuthProvider(
            idp=idp, user_pool_id="sa-east-1_unit", client_id="client-id"
        )

        with self.assertRaises(ExternalServiceError):
            provider.user_exists("owner@example.com")

    def test_set_permanent_password_calls_admin_set_user_password(self) -> None:
        idp = FakeCognitoClient()
        provider = CognitoAuthProvider(
            idp=idp, user_pool_id="sa-east-1_unit", client_id="client-id"
        )

        provider.set_permanent_password(
            username="owner@example.com",
            password="NewPermanentPass123!",
        )

        self.assertEqual(
            idp.admin_set_user_password_calls[0],
            {
                "UserPoolId": "sa-east-1_unit",
                "Username": "owner@example.com",
                "Password": "NewPermanentPass123!",
                "Permanent": True,
            },
        )

    def test_set_permanent_password_maps_invalid_password(self) -> None:
        for code in ("InvalidParameterException", "InvalidPasswordException"):
            with self.subTest(code=code):
                idp = FakeCognitoClient(admin_set_user_password_response=_client_error(code))
                provider = CognitoAuthProvider(
                    idp=idp, user_pool_id="sa-east-1_unit", client_id="client-id"
                )

                with self.assertRaises(InvalidChallengeResponseError):
                    provider.set_permanent_password(
                        username="owner@example.com",
                        password="short",
                    )

    def test_maps_unexpected_cognito_error_as_external_service_error(self) -> None:
        idp = FakeCognitoClient(refresh_response=_client_error("InternalErrorException"))
        provider = CognitoAuthProvider(
            idp=idp, user_pool_id="sa-east-1_unit", client_id="client-id"
        )

        with self.assertRaises(ExternalServiceError):
            provider.refresh(RefreshCommand(refresh_token="refresh-token"))


if __name__ == "__main__":
    unittest.main()
