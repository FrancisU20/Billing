"""
Ejecuta un Lambda handler localmente con un evento de prueba.

Uso:
  python run_lambda.py <module.handler> <event.json>

Ejemplos:
  python run_lambda.py lambda_handlers.invoice_worker_handler ../events/invoice_worker.json
  python run_lambda.py lambda_handlers.email_dispatch_handler ../events/email_dispatch.json
"""
from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(_BACKEND_DIR))


@dataclass
class LocalLambdaContext:
    """Simula el LambdaContext que AWS inyecta en cada invocación."""
    function_name: str = "local-debug"
    function_version: str = "$LATEST"
    memory_limit_in_mb: int = 256
    aws_request_id: str = "local-debug-request"
    log_group_name: str = "/aws/lambda/local-debug"
    log_stream_name: str = "local"
    remaining_time_in_millis: int = field(default=30_000, repr=False)

    def get_remaining_time_in_millis(self) -> int:
        return self.remaining_time_in_millis


class LambdaRunner:
    """Carga e invoca un handler Lambda con un evento JSON."""

    def __init__(self, module_path: str, event_file: Path) -> None:
        self._module_path, _, self._handler_name = module_path.rpartition(".")
        self._event = json.loads(event_file.read_text())
        self._context = LocalLambdaContext()

    def run(self) -> dict:
        module = importlib.import_module(self._module_path)
        handler = getattr(module, self._handler_name)

        if asyncio.iscoroutinefunction(handler):
            return asyncio.run(handler(self._event, self._context))
        return handler(self._event, self._context)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ejecuta un Lambda handler localmente")
    parser.add_argument("handler", help="Módulo y función (ej: lambda_handlers.invoice_worker_handler.handler)")
    parser.add_argument("event", type=Path, help="Ruta al JSON del evento SQS")
    args = parser.parse_args()

    print(f"⚡  Ejecutando: {args.handler}")
    print(f"📄  Evento:    {args.event}\n")

    result = LambdaRunner(args.handler, args.event).run()

    print("\n✅  Resultado:")
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
