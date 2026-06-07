"""
Brevo implementation of the EmailSender port.

Uses urllib3 (already bundled via boto3) to avoid extra dependencies.
The API key is fetched from Secrets Manager with an in-memory cache (TTL 5 min).
The temporary password is NEVER logged at any level.

Note: the HTML email body is in Spanish on purpose — it is user-facing
content delivered to Ecuadorian customers, not source code.
"""
from __future__ import annotations

import json

import urllib3

from lambdas.workers.email_notifications.ports import EmailSender
from shared.config import env
from shared.logger import get_logger
from shared.secrets.client import get_secret

_log = get_logger(__name__)

_BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
_SECRET_NAME   = env("BREVO_SECRET_NAME")
_SENDER_EMAIL  = env("BREVO_SENDER_EMAIL", "noreply@codelabsecuador.com")
_SENDER_NAME   = env("BREVO_SENDER_NAME",  "CodeLabs Billing")

_http = urllib3.PoolManager()


def _build_html(legal_rep_name: str, email: str, temp_password: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,sans-serif">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td align="center" style="padding:40px 20px">
        <table width="600" cellpadding="0" cellspacing="0"
               style="background:#ffffff;border-radius:8px;overflow:hidden">

          <tr>
            <td style="background:#1a1a2e;padding:32px 40px">
              <h1 style="margin:0;color:#ffffff;font-size:22px;font-weight:700">
                CodeLabs Billing
              </h1>
            </td>
          </tr>

          <tr>
            <td style="padding:40px">
              <h2 style="margin:0 0 16px;color:#1a1a2e;font-size:20px">
                Bienvenido, {legal_rep_name}
              </h2>
              <p style="margin:0 0 24px;color:#444;line-height:1.6">
                Tu cuenta en CodeLabs Billing ha sido creada exitosamente.
                A continuación encontrarás tus credenciales de acceso inicial.
              </p>

              <div style="background:#f8f9fa;border-left:4px solid #1a1a2e;
                          border-radius:4px;padding:20px;margin:0 0 24px">
                <p style="margin:0 0 8px;color:#666;font-size:13px;
                           text-transform:uppercase;letter-spacing:0.5px">
                  Credenciales de acceso
                </p>
                <p style="margin:0 0 6px;color:#1a1a2e">
                  <strong>Usuario:</strong> {email}
                </p>
                <p style="margin:0;color:#1a1a2e">
                  <strong>Contraseña temporal:</strong>
                  <code style="background:#e9ecef;padding:2px 6px;border-radius:3px;
                               font-size:15px">{temp_password}</code>
                </p>
              </div>

              <p style="margin:0 0 16px;color:#444;line-height:1.6">
                Al ingresar por primera vez se te pedirá establecer una
                contraseña permanente.
              </p>
              <p style="margin:0;color:#888;font-size:13px">
                Por seguridad, esta contraseña temporal caduca en 7 días.
                Si tienes problemas para acceder, contacta a tu administrador.
              </p>
            </td>
          </tr>

          <tr>
            <td style="background:#f8f9fa;padding:20px 40px;
                       border-top:1px solid #e9ecef">
              <p style="margin:0;color:#aaa;font-size:12px;text-align:center">
                © CodeLabs Billing · Ecuador
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


class BrevoEmailSender(EmailSender):
    def send_welcome(
        self, *, email: str, legal_rep_name: str, temp_password: str
    ) -> None:
        api_key = get_secret(_SECRET_NAME)

        payload = {
            "sender":      {"name": _SENDER_NAME, "email": _SENDER_EMAIL},
            "to":          [{"email": email, "name": legal_rep_name}],
            "subject":     "Bienvenido a CodeLabs Billing — tus credenciales de acceso",
            "htmlContent": _build_html(legal_rep_name, email, temp_password),
        }

        response = _http.request(
            "POST",
            _BREVO_API_URL,
            headers={
                "accept":       "application/json",
                "content-type": "application/json",
                "api-key":      api_key,
            },
            body=json.dumps(payload).encode("utf-8"),
        )

        if response.status >= 400:
            _log.error(
                "Brevo API error",
                status  = response.status,
                snippet = response.data.decode("utf-8")[:300],
            )
            raise RuntimeError(f"Brevo responded {response.status}")

        _log.info("Brevo: email sent", email=email, status=response.status)
