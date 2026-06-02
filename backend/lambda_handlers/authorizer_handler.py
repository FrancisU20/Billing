import os
import json
import urllib.request
import urllib.parse
from functools import lru_cache
from jose import jwk, jwt
from jose.utils import base64url_decode
from aws_lambda_powertools import Logger

logger = Logger(service="codelabs-billing-authorizer")

REGION = os.environ.get("AWS_REGION_NAME", "sa-east-1")
USER_POOL_ID = os.environ.get("COGNITO_USER_POOL_ID", "")
CLIENT_ID = os.environ.get("COGNITO_WEB_CLIENT_ID", "")
JWKS_URL = f"https://cognito-idp.{REGION}.amazonaws.com/{USER_POOL_ID}/.well-known/jwks.json"


@lru_cache(maxsize=1)
def get_jwks() -> dict:
    with urllib.request.urlopen(JWKS_URL) as response:
        return json.loads(response.read())


def handler(event: dict, context) -> dict:
    token = _extract_token(event)
    if not token:
        return _deny("Unauthorized")

    try:
        claims = _verify_token(token)
    except Exception as e:
        logger.warning("Token verification failed", extra={"error": str(e)})
        return _deny("Unauthorized")

    tenant_id = claims.get("custom:tenant_id", "")
    role = claims.get("custom:role", "viewer")
    is_superadmin = str(claims.get("custom:is_superadmin", "false")).lower() == "true"
    user_id = claims.get("sub", "")

    return _allow(
        principal_id=user_id,
        method_arn=event.get("methodArn", "*"),
        context={
            "tenant_id": tenant_id,
            "user_id": user_id,
            "role": role,
            "is_superadmin": str(is_superadmin),
        },
    )


def _extract_token(event: dict) -> str | None:
    auth_header = (
        event.get("authorizationToken")
        or event.get("headers", {}).get("Authorization")
        or event.get("headers", {}).get("authorization")
        or ""
    )
    if auth_header.startswith("Bearer "):
        return auth_header.removeprefix("Bearer ")
    return None


def _verify_token(token: str) -> dict:
    jwks = get_jwks()
    headers = jwt.get_unverified_headers(token)
    kid = headers.get("kid")

    key_data = next((k for k in jwks["keys"] if k["kid"] == kid), None)
    if not key_data:
        raise ValueError(f"No matching key found for kid={kid}")

    public_key = jwk.construct(key_data)
    claims = jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],
        audience=CLIENT_ID,
        options={"verify_exp": True},
    )
    return claims


def _allow(principal_id: str, method_arn: str, context: dict) -> dict:
    # Permitir acceso a todo el stage para evitar generar una política nueva por endpoint
    arn_parts = method_arn.split(":")
    region = arn_parts[3]
    account = arn_parts[4]
    api_gateway_arn = arn_parts[5]
    api_id, stage = api_gateway_arn.split("/")[:2]

    resource_arn = f"arn:aws:execute-api:{region}:{account}:{api_id}/{stage}/*/*"

    return {
        "principalId": principal_id,
        "policyDocument": {
            "Version": "2012-10-17",
            "Statement": [{"Action": "execute-api:Invoke", "Effect": "Allow", "Resource": resource_arn}],
        },
        "context": context,
    }


def _deny(message: str) -> dict:
    raise Exception(message)  # API Gateway interpreta excepciones como 401
