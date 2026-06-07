"""
Local server — simulates API Gateway HTTP API + Lambda Authorizer.

Locally there is no SQS trigger. By default workers do not run inline;
enable them with LOCAL_RUN_WORKERS_INLINE=true for targeted testing.

Start: make run
"""
from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

_ROOT    = Path(__file__).parent.parent
_LOCAL   = Path(__file__).parent
_BACKEND = _ROOT / "backend"

sys.path.insert(0, str(_BACKEND))
sys.path.insert(0, str(_LOCAL))

from dotenv import load_dotenv
load_dotenv(_LOCAL / ".env", override=True)

import re
import uuid
import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from event_builder import build_event
from context import LocalContext

import lambdas.tenants.handler as tenants_handler
import lambdas.plans.handler as plans_handler
import lambdas.auth.handler as auth_handler
# import lambdas.clients.handler as clients_handler

_LAMBDA_ROUTES: list[tuple[re.Pattern, object]] = [
    (re.compile(r"^/tenants(/.*)?$"), tenants_handler),
    (re.compile(r"^/plans(/.*)?$"),   plans_handler),
    (re.compile(r"^/auth(/.*)?$"),    auth_handler),
    # (re.compile(r"^/clients(/.*)?$"), clients_handler),
]


def _find_handler(path: str):
    for pattern, handler in _LAMBDA_ROUTES:
        if pattern.match(path):
            return handler
    return None


def _trigger_workers(path: str, method: str, response_body: dict) -> None:
    """
    Runs workers inline only if LOCAL_RUN_WORKERS_INLINE=true.
    In production the flow is: outbox → OutboxRelay → SQS → Lambda.

    Local notifications flow:
      tenant_onboarding runs inline → creates the user in Cognito (real AWS)
                                    → publishes OwnerCreatedEvent to EMAIL_NOTIFICATIONS_QUEUE_URL
      If EMAIL_NOTIFICATIONS_QUEUE_URL is set → the deployed Lambda
      processes the message and sends the email via Brevo.
      If empty → the event is dropped and no email is sent (dev without email).
    """
    if os.environ.get("LOCAL_RUN_WORKERS_INLINE", "false").lower() != "true":
        return

    if method == "POST" and path == "/tenants" and response_body.get("success"):
        import lambdas.workers.tenant_onboarding.handler as onboarding_worker

        data = response_body.get("data", {})
        sqs_event = {
            "Records": [{
                "messageId":     str(uuid.uuid4()),
                "receiptHandle": "local",
                "body": json.dumps({
                    "event_type":  "TenantCreatedEvent",
                    "event_id":    str(uuid.uuid4()),
                    "occurred_at": data.get("created_at", ""),
                    "data": {
                        "tenant_id":      data.get("id", ""),
                        "ruc":            data.get("ruc", ""),
                        "email":          data.get("email", ""),
                        "legal_rep_name": data.get("legal_rep_name", ""),
                    },
                }),
                "attributes": {},
            }]
        }
        onboarding_worker.handler(sqs_event, LocalContext())
        # email_notifications is triggered via real SQS (EMAIL_NOTIFICATIONS_QUEUE_URL)
        # when the Lambda is deployed. Locally without deploy, the event is dropped.


app = FastAPI(title="CodeLabs Billing — Local", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/_health", include_in_schema=False)
def health():
    return {"status": "ok", "server": "local"}


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"])
async def proxy(request: Request, path: str) -> Response:
    full_path = f"/{path}"
    handler   = _find_handler(full_path)

    if handler is None:
        return Response(
            content     = json.dumps({"success": False, "error": {"code": "NOT_FOUND", "message": f"Ruta no registrada: {full_path}"}}),  # noqa: client-facing ES
            status_code = 404,
            media_type  = "application/json",
        )

    body   = await request.body()
    event  = build_event(method=request.method, path=full_path,
                         headers=dict(request.headers),
                         query=dict(request.query_params), body=body)
    ctx    = LocalContext()
    result = handler.handler(event, ctx)

    # Run workers inline after successful operations
    if result.get("statusCode", 0) in (200, 201):
        try:
            response_body = json.loads(result.get("body", "{}"))
            _trigger_workers(full_path, request.method, response_body)
        except Exception:
            print("Local worker failed after the HTTP response:")
            traceback.print_exc()

    return Response(
        content     = result.get("body", ""),
        status_code = result.get("statusCode", 200),
        headers     = result.get("headers", {"Content-Type": "application/json"}),
        media_type  = "application/json",
    )


if __name__ == "__main__":
    port = int(os.environ.get("LOCAL_PORT", 8080))
    workers = os.environ.get("LOCAL_RUN_WORKERS_INLINE", "false").lower()
    email_q  = os.environ.get("EMAIL_NOTIFICATIONS_QUEUE_URL", "(vacío — sin email)")
    print("\n  CodeLabs Billing — Local Server")
    print(f"  http://localhost:{port}")
    print(f"  Workers inline:       {workers}")
    print(f"  Email notifications:  {email_q[:60] if email_q else '(vacío — sin email)'}")
    print("  DynamoDB: AWS dev tables\n")
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True,
                reload_dirs=[str(_BACKEND), str(_LOCAL)], app_dir=str(_LOCAL))
