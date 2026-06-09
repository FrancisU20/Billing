#!/usr/bin/env python3
"""
Crea el usuario superadmin en Cognito.

Uso:
    python scripts/create_superadmin.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import boto3

_ROOT = Path(__file__).resolve().parent.parent
_ENV_FILE = _ROOT / ".env"


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


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"ERROR: falta {name} en variables de entorno o .env")
        sys.exit(1)
    return value


def get_user_pool_id(cf, env_name: str) -> str:
    env_pool_id = os.environ.get("COGNITO_USER_POOL_ID", "").strip()
    if env_pool_id:
        return env_pool_id

    resp = cf.describe_stacks(StackName=f"CodeLabsBilling-{env_name.capitalize()}-Auth")
    outputs = {
        o["OutputKey"]: o["OutputValue"] for o in resp["Stacks"][0].get("Outputs", [])
    }
    pool_id = outputs.get("UserPoolId")
    if not pool_id:
        print("ERROR: No se encontró UserPoolId. Corre: make deploy")
        sys.exit(1)
    return pool_id


def _superadmin_attributes(email: str) -> list[dict[str, str]]:
    return [
        {"Name": "email", "Value": email},
        {"Name": "email_verified", "Value": "true"},
        {"Name": "custom:role", "Value": "superadmin"},
        {"Name": "custom:is_superadmin", "Value": "true"},
        {"Name": "custom:tenant_id", "Value": ""},
    ]


def main() -> None:
    _load_dotenv(_ENV_FILE)

    aws_profile = os.environ.get("AWS_PROFILE", "codelabs")
    aws_region = os.environ.get("AWS_REGION", "sa-east-1")
    env_name = os.environ.get("ENV", "dev")
    email = _required_env("SUPERADMIN_EMAIL")
    password = _required_env("SUPERADMIN_PASSWORD")

    session = boto3.Session(profile_name=aws_profile, region_name=aws_region)
    cf = session.client("cloudformation")
    idp = session.client("cognito-idp")

    pool_id = get_user_pool_id(cf, env_name)
    print(f"User Pool: {pool_id}")

    try:
        idp.admin_create_user(
            UserPoolId=pool_id,
            Username=email,
            UserAttributes=_superadmin_attributes(email),
            MessageAction="SUPPRESS",
        )
        print(f"✓ Superadmin creado: {email}")
    except idp.exceptions.UsernameExistsException:
        print(f"El usuario {email} ya existe. Sincronizando atributos y contraseña.")
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    try:
        idp.admin_update_user_attributes(
            UserPoolId=pool_id,
            Username=email,
            UserAttributes=_superadmin_attributes(email),
        )
        idp.admin_set_user_password(
            UserPoolId=pool_id,
            Username=email,
            Password=password,
            Permanent=True,
        )
        print("✓ Superadmin listo para login SRP")
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
