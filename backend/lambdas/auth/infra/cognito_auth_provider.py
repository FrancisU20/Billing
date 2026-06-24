from __future__ import annotations

"""Cognito implementation of the auth provider port."""

from typing import Any

import boto3
from botocore.exceptions import ClientError

from lambdas.auth.domain.commands import (
    LoginCommand,
    LogoutCommand,
    RefreshCommand,
    RespondChallengeCommand,
)
from lambdas.auth.domain.errors import AuthChallengeFailedError, InvalidChallengeResponseError
from lambdas.auth.domain.repositories.i_auth_provider import IAuthProvider
from lambdas.auth.domain.results import AuthChallenge, AuthOutcome, AuthTokens
from lambdas.auth.infra.srp import CognitoSrpSession
from shared.config import env
from shared.errors import ExternalServiceError, InvalidCredentialsError
from shared.logger import get_logger

_log = get_logger(__name__)
_SECRET_CHALLENGE_PARAMETERS = {"SALT", "SRP_B", "SECRET_BLOCK"}


class CognitoAuthProvider(IAuthProvider):
    def __init__(
        self,
        *,
        idp=None,
        user_pool_id: str | None = None,
        client_id: str | None = None,
    ) -> None:
        self._user_pool_id = user_pool_id or env("COGNITO_USER_POOL_ID")
        self._client_id = client_id or env("COGNITO_WEB_CLIENT_ID")
        self._idp = idp or boto3.client("cognito-idp")

    def login(self, command: LoginCommand) -> AuthOutcome:
        try:
            srp = CognitoSrpSession(
                user_pool_id=self._user_pool_id,
                username=command.username,
                password=command.password,
            )
            init_response = self._idp.initiate_auth(
                ClientId=self._client_id,
                AuthFlow="USER_SRP_AUTH",
                AuthParameters={
                    "USERNAME": command.username,
                    "SRP_A": srp.srp_a,
                },
            )

            if init_response.get("ChallengeName") != "PASSWORD_VERIFIER":
                return self._outcome_from_response(init_response)

            final_response = self._idp.respond_to_auth_challenge(
                ClientId=self._client_id,
                ChallengeName="PASSWORD_VERIFIER",
                ChallengeResponses=srp.challenge_responses(init_response["ChallengeParameters"]),
            )
            return self._outcome_from_response(
                final_response,
                # Un challenge encadenado (p.ej. NEW_PASSWORD_REQUIRED tras
                # PASSWORD_VERIFIER) no repite USER_ID_FOR_SRP en sus propias
                # ChallengeParameters. RespondToAuthChallenge exige USERNAME =
                # USER_ID_FOR_SRP del paso SRP inicial, no el alias de login.
                user_id_for_srp=init_response["ChallengeParameters"].get("USER_ID_FOR_SRP"),
            )

        except ClientError as exc:
            raise self._map_client_error(exc) from exc

    def refresh(self, command: RefreshCommand) -> AuthOutcome:
        try:
            response = self._idp.initiate_auth(
                ClientId=self._client_id,
                AuthFlow="REFRESH_TOKEN_AUTH",
                AuthParameters={"REFRESH_TOKEN": command.refresh_token},
            )
            return self._outcome_from_response(response)

        except ClientError as exc:
            raise self._map_client_error(exc) from exc

    def logout(self, command: LogoutCommand) -> None:
        try:
            self._idp.global_sign_out(AccessToken=command.access_token)
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code == "NotAuthorizedException":
                return
            raise self._map_client_error(exc) from exc

    def respond_to_challenge(self, command: RespondChallengeCommand) -> AuthOutcome:
        try:
            response = self._idp.respond_to_auth_challenge(
                ClientId=self._client_id,
                ChallengeName=command.challenge_name,
                Session=command.session,
                ChallengeResponses=command.responses,
            )
            return self._outcome_from_response(response)

        except ClientError as exc:
            raise self._map_client_error(exc) from exc

    def user_exists(self, username: str) -> bool:
        try:
            self._idp.admin_get_user(UserPoolId=self._user_pool_id, Username=username)
            return True
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code == "UserNotFoundException":
                return False
            raise self._map_client_error(exc) from exc

    def set_permanent_password(self, *, username: str, password: str) -> None:
        try:
            self._idp.admin_set_user_password(
                UserPoolId=self._user_pool_id,
                Username=username,
                Password=password,
                Permanent=True,
            )
        except ClientError as exc:
            raise self._map_client_error(exc) from exc

    def _outcome_from_response(
        self, response: dict[str, Any], *, user_id_for_srp: str | None = None
    ) -> AuthOutcome:
        if response.get("AuthenticationResult"):
            return self._tokens_from_result(response["AuthenticationResult"])

        challenge_name = response.get("ChallengeName", "")
        session = response.get("Session", "")
        if challenge_name and session:
            return AuthChallenge(
                challenge_name=challenge_name,
                session=session,
                parameters=self._sanitize_challenge_parameters(
                    response.get("ChallengeParameters", {}),
                    user_id_for_srp=user_id_for_srp,
                ),
            )

        _log.warning("unexpected Cognito auth response", response_keys=list(response.keys()))
        raise AuthChallengeFailedError()

    def _tokens_from_result(self, result: dict[str, Any]) -> AuthTokens:
        id_token = result.get("IdToken", "")
        access_token = result.get("AccessToken", "")
        expires_in = result.get("ExpiresIn")
        token_type = result.get("TokenType", "")
        if not id_token or not access_token or not expires_in or not token_type:
            _log.warning(
                "Cognito auth result missing required token fields",
                result_keys=list(result.keys()),
            )
            raise ExternalServiceError(detail="IncompleteAuthenticationResult")

        return AuthTokens(
            id_token=id_token,
            access_token=access_token,
            refresh_token=result.get("RefreshToken"),
            expires_in=int(expires_in),
            token_type=token_type,
        )

    def _sanitize_challenge_parameters(
        self, parameters: dict[str, str], *, user_id_for_srp: str | None = None
    ) -> dict[str, str]:
        sanitized = {
            key: value
            for key, value in parameters.items()
            if key not in _SECRET_CHALLENGE_PARAMETERS
        }
        username = parameters.get("USER_ID_FOR_SRP") or user_id_for_srp
        if username:
            sanitized["username"] = username
        return sanitized

    def _map_client_error(self, exc: ClientError) -> Exception:
        code = exc.response.get("Error", {}).get("Code", "ClientError")
        if code in {
            "NotAuthorizedException",
            "UserNotFoundException",
            "PasswordResetRequiredException",
            "UserNotConfirmedException",
        }:
            return InvalidCredentialsError(detail=code)

        if code in {
            "CodeMismatchException",
            "ExpiredCodeException",
            "InvalidParameterException",
            "InvalidPasswordException",
        }:
            return InvalidChallengeResponseError(detail=code)

        _log.error("Cognito client error", code=code)
        return ExternalServiceError(detail=code)
