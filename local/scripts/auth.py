"""
Autenticación Cognito para entorno local.
Devuelve el ID Token listo para usar en Postman / curl.
"""
from __future__ import annotations

import argparse
import getpass

from pycognito import Cognito

_USER_POOL_ID = "sa-east-1_IdhXX9uf6"
_CLIENT_ID = "2ljmd2kv56tuba6rjd04maf3jl"


class CognitoAuth:
    """Autenticación SRP contra Cognito."""

    def __init__(
        self,
        user_pool_id: str = _USER_POOL_ID,
        client_id: str = _CLIENT_ID,
    ) -> None:
        self._pool_id = user_pool_id
        self._client_id = client_id

    def get_id_token(self, email: str, password: str) -> str:
        user = Cognito(self._pool_id, self._client_id, username=email)
        user.authenticate(password=password)
        return user.id_token


def main() -> None:
    parser = argparse.ArgumentParser(description="Obtén un Bearer token de Cognito")
    parser.add_argument("email", nargs="?", help="Email del usuario")
    args = parser.parse_args()

    email = args.email or input("Email: ").strip()
    password = getpass.getpass("Password: ")

    token = CognitoAuth().get_id_token(email, password)

    print("\n📋  Bearer token (copia en Postman → Authorization):\n")
    print(f"Bearer {token}\n")


if __name__ == "__main__":
    main()
