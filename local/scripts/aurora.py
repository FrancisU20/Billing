"""
Gestión del túnel SSM hacia Aurora para desarrollo local.

Flujo:
  open()  → localiza el NAT instance → abre túnel SSM localhost:5432 → Aurora
  close() → mata el proceso SSM → túnel cerrado

Aurora nunca tiene IP pública. El tráfico va cifrado por SSM hasta el
NAT instance dentro de la VPC, de ahí a Aurora por red privada.
"""
from __future__ import annotations

import argparse
import json
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import boto3

_AWS_PROFILE = "codelabs"
_AWS_REGION = "sa-east-1"
_STACK_NAME = "CodeLabsBilling-Dev-Network"
_AURORA_HOST = "codelabs-billing-dev.cluster-c56oy8qwo6ie.sa-east-1.rds.amazonaws.com"
_LOCAL_PORT = 5432
_REMOTE_PORT = 5432
_PID_FILE = Path.home() / ".codelabs-ssm-tunnel.pid"
_TUNNEL_READY_TIMEOUT = 20  # segundos


def _get_nat_instance_id() -> str:
    """Obtiene el ID del NAT instance del stack de red."""
    session = boto3.Session(profile_name=_AWS_PROFILE, region_name=_AWS_REGION)
    ec2 = session.client("ec2")
    resp = ec2.describe_instances(
        Filters=[
            {"Name": "tag:aws:cloudformation:stack-name", "Values": [_STACK_NAME]},
            {"Name": "instance-state-name", "Values": ["running"]},
        ]
    )
    instances = [
        i
        for r in resp["Reservations"]
        for i in r["Instances"]
    ]
    if not instances:
        raise RuntimeError(f"No se encontró el NAT instance en el stack {_STACK_NAME}")
    return instances[0]["InstanceId"]


def _wait_for_tunnel(timeout: int = _TUNNEL_READY_TIMEOUT) -> bool:
    """Espera hasta que el puerto local responda (túnel listo)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", _LOCAL_PORT), timeout=1):
                return True
        except (ConnectionRefusedError, OSError):
            time.sleep(0.5)
    return False


class AuroraGuard:
    """Context manager que abre el túnel SSM al entrar y lo cierra al salir."""

    def __init__(
        self,
        profile: str = _AWS_PROFILE,
        region: str = _AWS_REGION,
    ) -> None:
        self._profile = profile
        self._region = region
        self._process: subprocess.Popen | None = None

    def open(self) -> None:
        nat_id = _get_nat_instance_id()
        print(f"🔌  NAT instance: {nat_id}")
        print(f"🚇  Abriendo túnel SSM: localhost:{_LOCAL_PORT} → Aurora")

        params = json.dumps({
            "portNumber": [str(_REMOTE_PORT)],
            "localPortNumber": [str(_LOCAL_PORT)],
            "host": [_AURORA_HOST],
        })

        self._process = subprocess.Popen(
            [
                "aws", "ssm", "start-session",
                "--target", nat_id,
                "--document-name", "AWS-StartPortForwardingSessionToRemoteHost",
                "--parameters", params,
                "--profile", self._profile,
                "--region", self._region,
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        _PID_FILE.write_text(str(self._process.pid))

        if _wait_for_tunnel():
            print(f"✅  Túnel activo — localhost:{_LOCAL_PORT} → Aurora")
        else:
            self.close()
            raise RuntimeError(
                "El túnel SSM no respondió a tiempo.\n"
                "Verifica que el NAT instance tenga AmazonSSMManagedInstanceCore."
            )

    def close(self) -> None:
        pid = self._read_pid()
        if pid:
            try:
                import os
                os.killpg(os.getpgid(pid), signal.SIGTERM)
            except ProcessLookupError:
                pass
            _PID_FILE.unlink(missing_ok=True)
            self._process = None
            print(f"🔒  Túnel SSM cerrado")
        else:
            print("ℹ️   No hay túnel SSM activo")

    def __enter__(self) -> AuroraGuard:
        self.open()
        return self

    def __exit__(self, *_) -> None:
        self.close()

    @staticmethod
    def _read_pid() -> int | None:
        try:
            return int(_PID_FILE.read_text().strip())
        except (FileNotFoundError, ValueError):
            return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Túnel SSM hacia Aurora para dev local")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--open", action="store_true", help="Abre el túnel SSM")
    group.add_argument("--close", action="store_true", help="Cierra el túnel SSM")
    args = parser.parse_args()

    guard = AuroraGuard()
    if args.open:
        guard.open()
    else:
        guard.close()


if __name__ == "__main__":
    main()
