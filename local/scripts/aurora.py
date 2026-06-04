"""
Gestión del Security Group de Aurora para acceso local.
Abre/cierra el puerto 5432 para la IP pública del desarrollador.
"""
from __future__ import annotations

import argparse
import urllib.request
from typing import Any

import boto3
from botocore.exceptions import ClientError

_AURORA_SG_ID = "sg-0a91b34c9809657cb"
_AWS_PROFILE = "codelabs"
_AWS_REGION = "sa-east-1"
_DB_PORT = 5432


def get_public_ip() -> str:
    with urllib.request.urlopen("https://checkip.amazonaws.com", timeout=5) as r:
        return r.read().decode().strip()


class AuroraGuard:
    """Context manager que abre Aurora al entrar y la cierra al salir."""

    def __init__(
        self,
        sg_id: str = _AURORA_SG_ID,
        profile: str = _AWS_PROFILE,
        region: str = _AWS_REGION,
    ) -> None:
        self._sg_id = sg_id
        session = boto3.Session(profile_name=profile, region_name=region)
        self._ec2 = session.client("ec2")
        self.public_ip: str = ""

    # ── Public API ─────────────────────────────────────────────────────────

    def open(self) -> str:
        self.public_ip = get_public_ip()
        self._authorize(self.public_ip)
        print(f"✅  Aurora abierta → {self.public_ip}/32:5432")
        return self.public_ip

    def close(self) -> None:
        if not self.public_ip:
            self.public_ip = get_public_ip()
        self._revoke(self.public_ip)
        print(f"🔒  Aurora cerrada → {self.public_ip}/32 removida del SG")

    # ── Context manager ────────────────────────────────────────────────────

    def __enter__(self) -> AuroraGuard:
        self.open()
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    # ── Private ────────────────────────────────────────────────────────────

    def _permission(self, cidr: str) -> list[dict]:
        return [{
            "IpProtocol": "tcp",
            "FromPort": _DB_PORT,
            "ToPort": _DB_PORT,
            "IpRanges": [{"CidrIp": cidr, "Description": "Local dev — auto-managed"}],
        }]

    def _authorize(self, ip: str) -> None:
        try:
            self._ec2.authorize_security_group_ingress(
                GroupId=self._sg_id,
                IpPermissions=self._permission(f"{ip}/32"),
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "InvalidPermission.Duplicate":
                raise

    def _revoke(self, ip: str) -> None:
        try:
            self._ec2.revoke_security_group_ingress(
                GroupId=self._sg_id,
                IpPermissions=self._permission(f"{ip}/32"),
            )
        except ClientError as exc:
            if exc.response["Error"]["Code"] != "InvalidPermission.NotFound":
                raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Gestión del SG de Aurora para dev local")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--open", action="store_true", help="Abre Aurora a tu IP actual")
    group.add_argument("--close", action="store_true", help="Cierra Aurora (remueve tu IP)")
    args = parser.parse_args()

    guard = AuroraGuard()
    if args.open:
        guard.open()
    else:
        guard.close()


if __name__ == "__main__":
    main()
