#!/usr/bin/env python3
"""Obtain a Cognito token using USER_SRP_AUTH for the local superadmin."""
from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import hmac
import json
import os
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.exceptions import ClientError, ProfileNotFound

_ROOT = Path(__file__).resolve().parent.parent
_LOCAL_ENV = _ROOT / "local" / ".env"

_N_HEX = (
    "FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD1"
    "29024E088A67CC74020BBEA63B139B22514A08798E3404DD"
    "EF9519B3CD3A431B302B0A6DF25F14374FE1356D6D51C245"
    "E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7ED"
    "EE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3D"
    "C2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F"
    "83655D23DCA3AD961C62F356208552BB9ED529077096966D"
    "670C354E4ABC9804F1746C08CA18217C32905E462E36CE3B"
    "E39E772C180E86039B2783A2EC07A28FB5C55DF06F4C52C9"
    "DE2BCBF6955817183995497CEA956AE515D2261898FA0510"
    "15728E5A8AAAC42DAD33170D04507A33A85521ABDF1CBA64"
    "ECFB850458DBEF0A8AEA71575D060C7DB3970F85A6E1E4C7"
    "ABF5AE8CDB0933D71E8C94E04A25619DCEE3D2261AD2EE6B"
    "F12FFA06D98A0864D87602733EC86A64521F2B18177B200C"
    "BBE117577A615D6C770988C0BAD946E208E24FA074E5AB31"
    "43DB5BFCE0FD108E4B82D120A93AD2CAFFFFFFFFFFFFFFFF"
)
_N = int(_N_HEX, 16)
_G = 2
_INFO_BITS = b"Caldera Derived Key"
_WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key and key not in os.environ:
            os.environ[key] = value


def _hash_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _hex_hash(hex_string: str) -> str:
    return _hash_sha256(bytes.fromhex(hex_string))


def _pad_hex(value: int | str) -> str:
    hex_value = value if isinstance(value, str) else f"{value:x}"
    if len(hex_value) % 2 == 1:
        hex_value = "0" + hex_value
    elif hex_value[0] in "89ABCDEFabcdef":
        hex_value = "00" + hex_value
    return hex_value


def _hkdf(ikm: bytes, salt: bytes) -> bytes:
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    return hmac.new(prk, _INFO_BITS + b"\x01", hashlib.sha256).digest()[:16]


def _timestamp() -> str:
    now = datetime.now(timezone.utc)
    return (
        f"{_WEEKDAYS[now.weekday()]} {_MONTHS[now.month - 1]} {now.day} "
        f"{now:%H:%M:%S} UTC {now.year}"
    )


class CognitoSrpClient:
    def __init__(self, *, client_id: str, user_pool_id: str, username: str, password: str) -> None:
        self.client_id = client_id
        self.user_pool_id = user_pool_id
        self.username = username
        self.password = password
        self._a = secrets.randbits(1024)
        self._big_a = pow(_G, self._a, _N)
        if self._big_a % _N == 0:
            raise RuntimeError("SRP_A inválido")
        self._k = int(_hex_hash(_pad_hex(_N) + _pad_hex(_G)), 16)

    @property
    def srp_a(self) -> str:
        return f"{self._big_a:x}"

    def challenge_responses(self, challenge: dict) -> dict:
        user_id = challenge["USER_ID_FOR_SRP"]
        salt = int(challenge["SALT"], 16)
        big_b = int(challenge["SRP_B"], 16)
        secret_block = base64.b64decode(challenge["SECRET_BLOCK"])

        if big_b % _N == 0:
            raise RuntimeError("SRP_B inválido")

        u_value = int(_hex_hash(_pad_hex(self._big_a) + _pad_hex(big_b)), 16)
        if u_value == 0:
            raise RuntimeError("SRP_U inválido")

        pool_name = self.user_pool_id.split("_", 1)[1]
        user_password_hash = _hash_sha256(f"{pool_name}{user_id}:{self.password}".encode("utf-8"))
        x_value = int(_hex_hash(_pad_hex(salt) + user_password_hash), 16)
        s_value = pow(big_b - self._k * pow(_G, x_value, _N), self._a + u_value * x_value, _N)
        key = _hkdf(bytes.fromhex(_pad_hex(s_value)), bytes.fromhex(_pad_hex(u_value)))

        timestamp = _timestamp()
        signature = base64.b64encode(
            hmac.new(
                key,
                (pool_name + user_id).encode("utf-8") + secret_block + timestamp.encode("utf-8"),
                hashlib.sha256,
            ).digest()
        ).decode("utf-8")

        return {
            "USERNAME": user_id,
            "PASSWORD_CLAIM_SECRET_BLOCK": challenge["SECRET_BLOCK"],
            "PASSWORD_CLAIM_SIGNATURE": signature,
            "TIMESTAMP": timestamp,
        }


def _stack_outputs(session: boto3.Session, env_name: str) -> dict[str, str]:
    cf = session.client("cloudformation")
    response = cf.describe_stacks(StackName=f"CodeLabsBilling-{env_name.capitalize()}-Auth")
    return {
        output["OutputKey"]: output["OutputValue"]
        for output in response["Stacks"][0].get("Outputs", [])
    }


def _resolve_cognito_ids(session: boto3.Session, env_name: str) -> tuple[str, str]:
    user_pool_id = os.environ.get("COGNITO_USER_POOL_ID", "")
    client_id = os.environ.get("COGNITO_WEB_CLIENT_ID", "")
    if user_pool_id and client_id:
        return user_pool_id, client_id

    outputs = _stack_outputs(session, env_name)
    user_pool_id = user_pool_id or outputs.get("UserPoolId", "")
    client_id = client_id or outputs.get("WebClientId", "")
    if not user_pool_id or not client_id:
        raise RuntimeError("No se pudo resolver COGNITO_USER_POOL_ID/COGNITO_WEB_CLIENT_ID")
    return user_pool_id, client_id


def _parse_args() -> argparse.Namespace:
    _load_dotenv(_LOCAL_ENV)
    parser = argparse.ArgumentParser(description="Login Cognito SRP y muestra token del superadmin.")
    parser.add_argument("--env", default=os.environ.get("ENV", "dev"))
    parser.add_argument("--region", default=os.environ.get("AWS_REGION", "sa-east-1"))
    parser.add_argument("--profile", default=os.environ.get("AWS_PROFILE", "codelabs"))
    parser.add_argument(
        "--username",
        default=os.environ.get("SUPERADMIN_EMAIL") or os.environ.get("LOCAL_EMAIL", ""),
        help="Email del superadmin. También se puede usar SUPERADMIN_EMAIL en local/.env.",
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("SUPERADMIN_PASSWORD", ""),
        help="Password del superadmin. Preferir SUPERADMIN_PASSWORD en local/.env ignorado por git.",
    )
    parser.add_argument(
        "--token-type",
        choices=("id", "access", "refresh", "all"),
        default=os.environ.get("TOKEN_TYPE", "id"),
    )
    return parser.parse_args()


def _password_or_prompt(password: str) -> str:
    if password:
        return password
    if sys.stdin.isatty():
        return getpass.getpass("Superadmin password: ")
    raise RuntimeError("SUPERADMIN_PASSWORD es requerido cuando no hay TTY para pedir password")


def _authenticate(args: argparse.Namespace) -> dict:
    if not args.username:
        raise RuntimeError("SUPERADMIN_EMAIL es requerido")

    password = _password_or_prompt(args.password)
    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    user_pool_id, client_id = _resolve_cognito_ids(session, args.env)
    idp = session.client("cognito-idp")

    srp = CognitoSrpClient(
        client_id=client_id,
        user_pool_id=user_pool_id,
        username=args.username,
        password=password,
    )
    init_response = idp.initiate_auth(
        ClientId=client_id,
        AuthFlow="USER_SRP_AUTH",
        AuthParameters={
            "USERNAME": args.username,
            "SRP_A": srp.srp_a,
        },
    )

    challenge_name = init_response.get("ChallengeName")
    if challenge_name != "PASSWORD_VERIFIER":
        raise RuntimeError(f"Challenge Cognito no soportado: {challenge_name}")

    final_response = idp.respond_to_auth_challenge(
        ClientId=client_id,
        ChallengeName="PASSWORD_VERIFIER",
        ChallengeResponses=srp.challenge_responses(init_response["ChallengeParameters"]),
    )

    if final_response.get("ChallengeName"):
        raise RuntimeError(f"Challenge Cognito pendiente: {final_response['ChallengeName']}")
    return final_response["AuthenticationResult"]


def main() -> int:
    args = _parse_args()
    try:
        result = _authenticate(args)
    except ProfileNotFound as exc:
        print(f"ERROR: perfil AWS no encontrado: {exc}", file=sys.stderr)
        return 1
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "ClientError")
        message = exc.response.get("Error", {}).get("Message", str(exc))
        print(f"ERROR Cognito/AWS [{code}]: {message}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.token_type == "id":
        print(result["IdToken"])
    elif args.token_type == "access":
        print(result["AccessToken"])
    elif args.token_type == "refresh":
        print(result["RefreshToken"])
    else:
        print(json.dumps({
            "id_token": result["IdToken"],
            "access_token": result["AccessToken"],
            "refresh_token": result["RefreshToken"],
            "expires_in": result["ExpiresIn"],
            "token_type": result["TokenType"],
        }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
