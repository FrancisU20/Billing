"""
Orquestador del servidor de debug local.

Ciclo de vida:
  1. Abre Aurora al IP actual
  2. Obtiene token de Cognito y lo muestra
  3. Levanta uvicorn (con recarga automática)
  4. Ctrl+C → para uvicorn → cierra Aurora → salida limpia
"""
from __future__ import annotations

import getpass
import os
import signal
import subprocess
import sys
from pathlib import Path

from aurora import AuroraGuard
from auth import CognitoAuth

_BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
_UVICORN_CMD = [
    sys.executable, "-m", "uvicorn",
    "app.main:app",
    "--reload",
    "--port", "8000",
    "--env-file", str(_BACKEND_DIR / ".env.local"),
]


def _print_banner(ip: str, token: str) -> None:
    print("\n" + "─" * 60)
    print("  🚀  CodeLabs Billing — Debug Server")
    print("─" * 60)
    print(f"  🌐  API:    http://localhost:8000")
    print(f"  📖  Docs:   http://localhost:8000/docs")
    print(f"  🛢️   Aurora: {ip} → conectada")
    print("─" * 60)
    print("  📋  Bearer token para Postman:\n")
    print(f"  Bearer {token[:60]}...")
    print("\n  (token completo copiado en la terminal superior)")
    print("─" * 60)
    print("  Ctrl+C para cerrar\n")


def main() -> None:
    email = input("📧  Email Cognito: ").strip()
    password = getpass.getpass("🔑  Password: ")

    process: subprocess.Popen | None = None

    with AuroraGuard() as guard:
        print("\n🔐  Autenticando en Cognito...")
        token = CognitoAuth().get_id_token(email, password)
        print(f"\nBearer {token}\n")

        _print_banner(guard.public_ip, token)

        env = {**os.environ, "PYTHONPATH": str(_BACKEND_DIR)}
        process = subprocess.Popen(_UVICORN_CMD, cwd=_BACKEND_DIR, env=env)

        def _shutdown(sig: int, frame: object) -> None:
            print("\n\n🛑  Cerrando uvicorn...")
            if process and process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
            # AuroraGuard.__exit__ cierra el SG al salir del with

        signal.signal(signal.SIGINT, _shutdown)
        signal.signal(signal.SIGTERM, _shutdown)

        process.wait()

    print("✅  Entorno cerrado limpiamente\n")


if __name__ == "__main__":
    main()
