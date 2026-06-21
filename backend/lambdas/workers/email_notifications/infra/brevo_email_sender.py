from __future__ import annotations

"""
Brevo implementation of the EmailSender port.

Uses urllib3 (already bundled via boto3) to avoid extra dependencies.
The API key is fetched from Secrets Manager with an in-memory cache (TTL 5 min).
The temporary password is NEVER logged at any level.

Note: the HTML email body is in Spanish on purpose — it is user-facing
content delivered to Ecuadorian customers, not source code.
"""

import base64
import json
from html import escape

import urllib3

from lambdas.workers.email_notifications.ports import EmailSender
from shared.config import env
from shared.dates import format_date_ecuador, format_datetime_ecuador
from shared.errors import ExternalServiceError
from shared.logger import get_logger
from shared.secrets.client import get_secret

_log = get_logger(__name__)

_BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
_SECRET_NAME = env("BREVO_SECRET_NAME")
_SENDER_EMAIL = env("BREVO_SENDER_EMAIL", "no-reply@codelabsecuador.com")
_SENDER_NAME = env("BREVO_SENDER_NAME", "Wali")
_FRONTEND_URL = env("FRONTEND_URL", "")
# Logotipo Wali servido por el frontend desplegado (frontend/public/wordmark-dark.png) —
# evita duplicar el asset en el backend y los clientes de correo no renderizan SVG.
_WORDMARK_URL = f"{_FRONTEND_URL}/wordmark-dark.png"
_BRAND_INK = "#0D1126"
_BRAND_DANGER = "#b91c1c"

_http = urllib3.PoolManager()


def _render_header(subtitle: str | None = None, *, danger: bool = False) -> str:
    background = _BRAND_DANGER if danger else _BRAND_INK
    safe_subtitle = (
        f'<p style="margin:8px 0 0;color:#d1d5db;font-size:13px">{escape(subtitle, quote=True)}</p>'
        if subtitle
        else ""
    )
    return f"""
          <tr>
            <td style="background:{background};padding:28px 40px">
              <img src="{_WORDMARK_URL}" alt="Wali" width="150" height="59"
                   style="display:block;border:0;outline:none">
              {safe_subtitle}
            </td>
          </tr>"""


def _build_html(legal_rep_name: str, email: str, temp_password: str) -> str:
    safe_name = escape(legal_rep_name, quote=True)
    safe_email = escape(email, quote=True)
    safe_temp_password = escape(temp_password, quote=True)

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

          {_render_header()}

          <tr>
            <td style="padding:40px">
              <h2 style="margin:0 0 16px;color:#0D1126;font-size:20px">
                Bienvenido, {safe_name}
              </h2>
              <p style="margin:0 0 24px;color:#444;line-height:1.6">
                Tu cuenta en Wali ha sido creada exitosamente.
                A continuación encontrarás tus credenciales de acceso inicial.
              </p>

              <div style="background:#f8f9fa;border-left:4px solid #0D1126;
                          border-radius:4px;padding:20px;margin:0 0 24px">
                <p style="margin:0 0 8px;color:#666;font-size:13px;
                           text-transform:uppercase;letter-spacing:0.5px">
                  Credenciales de acceso
                </p>
                <p style="margin:0 0 6px;color:#0D1126">
                  <strong>Usuario:</strong> {safe_email}
                </p>
                <p style="margin:0;color:#0D1126">
                  <strong>Contraseña temporal:</strong>
                  <code style="background:#e9ecef;padding:2px 6px;border-radius:3px;
                               font-size:15px">{safe_temp_password}</code>
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
                © Wali · Ecuador
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _build_onboarding_otp_html(legal_rep_name: str, otp: str, expires_at: str) -> str:
    safe_name = escape(legal_rep_name, quote=True)
    safe_otp = escape(otp, quote=True)
    safe_expires_at = escape(_format_datetime(expires_at), quote=True)

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

          {_render_header()}

          <tr>
            <td style="padding:40px">
              <h2 style="margin:0 0 16px;color:#0D1126;font-size:20px">
                Verifica tu correo, {safe_name}
              </h2>
              <p style="margin:0 0 24px;color:#444;line-height:1.6">
                Usa este código para completar el registro de tu empresa.
              </p>

              <div style="background:#f8f9fa;border-left:4px solid #0D1126;
                          border-radius:4px;padding:20px;margin:0 0 24px;text-align:center">
                <p style="margin:0;color:#0D1126;font-size:32px;font-weight:700;
                          letter-spacing:6px">{safe_otp}</p>
              </div>

              <p style="margin:0;color:#888;font-size:13px">
                Este código expira en 10 minutos.
                Fecha técnica de expiración: {safe_expires_at}.
              </p>
            </td>
          </tr>

          <tr>
            <td style="background:#f8f9fa;padding:20px 40px;
                       border-top:1px solid #e9ecef">
              <p style="margin:0;color:#aaa;font-size:12px;text-align:center">
                © Wali · Ecuador
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _get_api_key() -> str:
    api_key = get_secret(_SECRET_NAME)
    # Secrets Manager puede almacenar el valor como string plano o como JSON.
    # Si es JSON {"api_key": "xkeysib-..."} lo extraemos; si ya es string, lo usamos directo.
    if isinstance(api_key, str) and api_key.startswith("{"):
        try:
            parsed = json.loads(api_key)
            api_key = parsed.get("api_key") or parsed.get("value") or api_key
        except (json.JSONDecodeError, AttributeError):
            pass
    if not api_key or not isinstance(api_key, str):
        raise ExternalServiceError("BREVO_SECRET_NAME no contiene un API key válido")
    return api_key


def _send(api_key: str, payload: dict, *, log_email: str) -> None:
    response = _http.request(
        "POST",
        _BREVO_API_URL,
        headers={
            "accept": "application/json",
            "content-type": "application/json",
            "api-key": api_key,
        },
        body=json.dumps(payload).encode("utf-8"),
    )

    if response.status >= 400:
        _log.error("Brevo API error", status=response.status)
        raise ExternalServiceError(f"Brevo responded {response.status}")

    _log.info("Brevo: email sent", email=log_email, status=response.status)


def _format_date(value: str) -> str:
    return format_date_ecuador(value)


def _format_datetime(value: str) -> str:
    return format_datetime_ecuador(value)


def _summary_row(label: str, value: str) -> str:
    safe_label = escape(label, quote=True)
    safe_value = escape(value or "No disponible", quote=True)
    return f"""
                <tr>
                  <td style="padding:8px 0;color:#6b7280;font-size:13px">{safe_label}</td>
                  <td align="right" style="padding:8px 0;color:#111827;font-size:13px;
                             font-weight:700">{safe_value}</td>
                </tr>"""


def _build_enterprise_lead_html(trade_name: str, ruc: str, email: str, plan_label: str) -> str:
    safe_trade_name = escape(trade_name, quote=True)
    safe_ruc = escape(ruc, quote=True)
    safe_email = escape(email, quote=True)
    safe_plan_label = escape(plan_label, quote=True)

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

          {_render_header()}

          <tr>
            <td style="padding:40px">
              <h2 style="margin:0 0 16px;color:#0D1126;font-size:20px">
                Nuevo lead Corporativo
              </h2>
              <p style="margin:0 0 24px;color:#444;line-height:1.6">
                Una empresa solicitó el plan Corporativo desde el formulario de
                registro. Contactar para continuar el proceso comercial.
              </p>

              <div style="background:#f8f9fa;border-left:4px solid #0D1126;
                          border-radius:4px;padding:20px;margin:0 0 24px">
                <p style="margin:0 0 6px;color:#0D1126">
                  <strong>Razón social:</strong> {safe_trade_name}
                </p>
                <p style="margin:0 0 6px;color:#0D1126">
                  <strong>RUC:</strong> {safe_ruc}
                </p>
                <p style="margin:0 0 6px;color:#0D1126">
                  <strong>Email de contacto:</strong> {safe_email}
                </p>
                <p style="margin:0;color:#0D1126">
                  <strong>Plan solicitado:</strong> {safe_plan_label}
                </p>
              </div>
            </td>
          </tr>

          <tr>
            <td style="background:#f8f9fa;padding:20px 40px;
                       border-top:1px solid #e9ecef">
              <p style="margin:0;color:#aaa;font-size:12px;text-align:center">
                © Wali · Ecuador
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _build_subscription_renewal_reminder_html(
    legal_rep_name: str,
    trade_name: str,
    plan_cycle_ends_at: str,
    days_remaining: int,
    renewal_url: str,
) -> str:
    safe_name = escape(legal_rep_name, quote=True)
    safe_trade_name = escape(trade_name, quote=True)
    safe_ends_at = escape(plan_cycle_ends_at, quote=True)
    safe_url = escape(renewal_url, quote=True)

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

          {_render_header()}

          <tr>
            <td style="padding:40px">
              <h2 style="margin:0 0 16px;color:#0D1126;font-size:20px">
                Hola, {safe_name}
              </h2>
              <p style="margin:0 0 24px;color:#444;line-height:1.6">
                La suscripción de <strong>{safe_trade_name}</strong> vence en
                <strong>{days_remaining} días</strong>. Renuévala para continuar
                emitiendo comprobantes electrónicos sin interrupciones.
              </p>

              <div style="background:#f8f9fa;border-left:4px solid #0D1126;
                          border-radius:4px;padding:20px;margin:0 0 24px">
                <p style="margin:0;color:#0D1126">
                  <strong>Vence el:</strong> {safe_ends_at}
                </p>
              </div>

              <a href="{safe_url}"
                 style="display:inline-block;background:#0D1126;color:#ffffff;
                        text-decoration:none;padding:14px 28px;border-radius:6px;
                        font-size:15px;font-weight:700;margin:0 0 24px">
                Renovar ahora &rarr;
              </a>

              <p style="margin:0;color:#888;font-size:13px">
                Si el botón no funciona, copia este enlace en tu navegador:<br>
                <a href="{safe_url}" style="color:#0D1126">{safe_url}</a>
              </p>
            </td>
          </tr>

          <tr>
            <td style="background:#f8f9fa;padding:20px 40px;
                       border-top:1px solid #e9ecef">
              <p style="margin:0;color:#aaa;font-size:12px;text-align:center">
                © Wali · Ecuador
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _build_subscription_expired_html(legal_rep_name: str, trade_name: str, renewal_url: str) -> str:
    safe_name = escape(legal_rep_name, quote=True)
    safe_trade_name = escape(trade_name, quote=True)
    safe_url = escape(renewal_url, quote=True)

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

          {_render_header()}

          <tr>
            <td style="padding:40px">
              <h2 style="margin:0 0 16px;color:#0D1126;font-size:20px">
                Hola, {safe_name}
              </h2>
              <p style="margin:0 0 24px;color:#444;line-height:1.6">
                La suscripción de <strong>{safe_trade_name}</strong> ha vencido y
                tu cuenta ha sido suspendida temporalmente. Para reactivar el acceso,
                realiza el pago de renovación.
              </p>

              <a href="{safe_url}"
                 style="display:inline-block;background:#b91c1c;color:#ffffff;
                        text-decoration:none;padding:14px 28px;border-radius:6px;
                        font-size:15px;font-weight:700;margin:0 0 24px">
                Reactivar cuenta &rarr;
              </a>

              <p style="margin:0;color:#888;font-size:13px">
                Si el botón no funciona, copia este enlace en tu navegador:<br>
                <a href="{safe_url}" style="color:#0D1126">{safe_url}</a><br><br>
                Una vez registrado el pago, tu cuenta se reactivará de inmediato.
              </p>
            </td>
          </tr>

          <tr>
            <td style="background:#f8f9fa;padding:20px 40px;
                       border-top:1px solid #e9ecef">
              <p style="margin:0;color:#aaa;font-size:12px;text-align:center">
                © Wali · Ecuador
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _build_certificate_expiry_alert_html(
    legal_rep_name: str, trade_name: str, ruc: str, cert_expires_at: str, days_remaining: int
) -> str:
    safe_name = escape(legal_rep_name, quote=True)
    safe_trade_name = escape(trade_name, quote=True)
    safe_ruc = escape(ruc, quote=True)
    safe_expires_at = escape(cert_expires_at, quote=True)

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

          {_render_header()}

          <tr>
            <td style="padding:40px">
              <h2 style="margin:0 0 16px;color:#0D1126;font-size:20px">
                Hola, {safe_name}
              </h2>
              <p style="margin:0 0 24px;color:#444;line-height:1.6">
                El certificado digital de <strong>{safe_trade_name}</strong> vence
                en <strong>{days_remaining} días</strong>. Renuévalo a tiempo para
                no interrumpir la emisión de comprobantes electrónicos.
              </p>

              <div style="background:#f8f9fa;border-left:4px solid #0D1126;
                          border-radius:4px;padding:20px;margin:0 0 24px">
                <p style="margin:0 0 6px;color:#0D1126">
                  <strong>RUC:</strong> {safe_ruc}
                </p>
                <p style="margin:0;color:#0D1126">
                  <strong>Fecha de vencimiento:</strong> {safe_expires_at}
                </p>
              </div>

              <p style="margin:0;color:#888;font-size:13px">
                Una vez renovado, sube el nuevo certificado desde tu panel para
                actualizarlo.
              </p>
            </td>
          </tr>

          <tr>
            <td style="background:#f8f9fa;padding:20px 40px;
                       border-top:1px solid #e9ecef">
              <p style="margin:0;color:#aaa;font-size:12px;text-align:center">
                © Wali · Ecuador
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _build_payment_failed_html(legal_rep_name: str, trade_name: str, renewal_url: str) -> str:
    safe_name = escape(legal_rep_name, quote=True)
    safe_trade_name = escape(trade_name, quote=True)
    safe_url = escape(renewal_url, quote=True)

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

          {_render_header()}

          <tr>
            <td style="padding:40px">
              <h2 style="margin:0 0 16px;color:#0D1126;font-size:20px">
                Hola, {safe_name}
              </h2>
              <p style="margin:0 0 24px;color:#444;line-height:1.6">
                No pudimos procesar el cobro automático de la suscripción de
                <strong>{safe_trade_name}</strong>. Tu tarjeta fue rechazada.
                Para mantener el acceso, realiza el pago manualmente.
              </p>

              <a href="{safe_url}"
                 style="display:inline-block;background:#b91c1c;color:#ffffff;
                        text-decoration:none;padding:14px 28px;border-radius:6px;
                        font-size:15px;font-weight:700;margin:0 0 24px">
                Pagar ahora &rarr;
              </a>

              <p style="margin:0;color:#888;font-size:13px">
                Si el botón no funciona, copia este enlace en tu navegador:<br>
                <a href="{safe_url}" style="color:#0D1126">{safe_url}</a><br><br>
                Una vez registrado el pago, tu cuenta continuará activa sin interrupciones.
              </p>
            </td>
          </tr>

          <tr>
            <td style="background:#f8f9fa;padding:20px 40px;
                       border-top:1px solid #e9ecef">
              <p style="margin:0;color:#aaa;font-size:12px;text-align:center">
                © Wali · Ecuador
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _build_orphan_payment_alert_html(
    order_id: str,
    payer_email: str,
    plan_id: str,
    amount: str,
    currency: str,
    confirmed_at: str,
) -> str:
    safe_order_id = escape(order_id, quote=True)
    safe_payer_email = escape(payer_email, quote=True)
    safe_plan_id = escape(plan_id, quote=True)
    safe_amount = escape(amount, quote=True)
    safe_currency = escape(currency, quote=True)
    safe_confirmed_at = escape(_format_datetime(confirmed_at), quote=True)

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

          {_render_header("Alerta operacional", danger=True)}

          <tr>
            <td style="padding:40px">
              <h2 style="margin:0 0 16px;color:#0D1126;font-size:20px">
                Pago sin cuenta asociada
              </h2>
              <p style="margin:0 0 24px;color:#444;line-height:1.6">
                Se detectó un pago en estado <strong>PAID</strong> que no tiene
                un tenant vinculado. El cliente fue cobrado pero su cuenta no fue creada.
                Revisar y crear el tenant manualmente si corresponde.
              </p>

              <div style="background:#fff1f2;border-left:4px solid #b91c1c;
                          border-radius:4px;padding:20px;margin:0 0 24px">
                <p style="margin:0 0 6px;color:#0D1126">
                  <strong>Order ID (dLocal):</strong> {safe_order_id}
                </p>
                <p style="margin:0 0 6px;color:#0D1126">
                  <strong>Email del pagador:</strong> {safe_payer_email}
                </p>
                <p style="margin:0 0 6px;color:#0D1126">
                  <strong>Plan:</strong> {safe_plan_id}
                </p>
                <p style="margin:0 0 6px;color:#0D1126">
                  <strong>Monto:</strong> {safe_amount} {safe_currency}
                </p>
                <p style="margin:0;color:#0D1126">
                  <strong>Confirmado el:</strong> {safe_confirmed_at}
                </p>
              </div>

              <p style="margin:0;color:#888;font-size:13px">
                Para recuperar: crear el tenant via <code>POST /tenants</code> y luego
                vincular el pago con <code>link_tenant(order_id, tenant_id)</code> en DynamoDB.
              </p>
            </td>
          </tr>

          <tr>
            <td style="background:#f8f9fa;padding:20px 40px;
                       border-top:1px solid #e9ecef">
              <p style="margin:0;color:#aaa;font-size:12px;text-align:center">
                © Wali · Ecuador
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _build_document_authorized_html(
    legal_rep_name: str,
    document_id: str,
    access_key: str,
    authorization_number: str,
    issuer_name: str,
    issuer_ruc: str,
    buyer_name: str,
    buyer_id: str,
    buyer_email: str,
    sequential_display: str,
    issued_at: str,
    authorized_at: str,
    total: str,
    currency: str,
) -> str:
    safe_name = escape(legal_rep_name, quote=True)
    safe_document_id = escape(document_id, quote=True)
    safe_access_key = escape(access_key, quote=True)
    safe_auth_number = escape(authorization_number, quote=True)
    safe_issuer = escape(issuer_name or "Emisor", quote=True)
    safe_issuer_ruc = escape(issuer_ruc, quote=True)
    safe_buyer = escape(buyer_name or "Comprador", quote=True)
    safe_buyer_id = escape(buyer_id, quote=True)
    safe_buyer_email = escape(buyer_email or "No registrado", quote=True)
    display_sequential = sequential_display or document_id
    display_issued_at = _format_date(issued_at)
    display_authorized_at = _format_datetime(authorized_at)
    display_total = f"{total or '0.00'} {currency or 'USD'}"

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

          {_render_header("Documento tributario electrónico autorizado")}

          <tr>
            <td style="padding:40px">
              <h2 style="margin:0 0 16px;color:#0D1126;font-size:20px">
                Hola, {safe_name}
              </h2>
              <p style="margin:0 0 24px;color:#444;line-height:1.6">
                Tu factura electrónica fue <strong>autorizada</strong> por el SRI.
                Este es el resumen del documento emitido.
              </p>

              <div style="background:#ecfdf5;border-left:4px solid #059669;
                          border-radius:4px;padding:18px;margin:0 0 24px">
                <p style="margin:0;color:#065f46;font-size:13px;font-weight:700">
                  Factura autorizada
                </p>
              </div>

              <div style="background:#f8f9fa;border-left:4px solid #0D1126;
                          border-radius:4px;padding:20px;margin:0 0 24px">
                <p style="margin:0 0 10px;color:#0D1126;font-size:14px;font-weight:700">
                  Resumen
                </p>
                <table width="100%" cellpadding="0" cellspacing="0">
                  {_summary_row("Tipo", "Factura")}
                  {_summary_row("Secuencial", display_sequential)}
                  {_summary_row("Fecha de emisión", display_issued_at)}
                  {_summary_row("Fecha de autorización", display_authorized_at)}
                  {_summary_row("Total", display_total)}
                </table>
              </div>

              <div style="margin:0 0 24px">
                <p style="margin:0 0 8px;color:#0D1126;font-size:14px;font-weight:700">
                  Emisor
                </p>
                <p style="margin:0;color:#444;font-size:13px;line-height:1.6">
                  {safe_issuer} ({safe_issuer_ruc})
                </p>
              </div>

              <div style="margin:0 0 24px">
                <p style="margin:0 0 8px;color:#0D1126;font-size:14px;font-weight:700">
                  Comprador
                </p>
                <p style="margin:0;color:#444;font-size:13px;line-height:1.6">
                  {safe_buyer} ({safe_buyer_id})<br>
                  {safe_buyer_email}
                </p>
              </div>

              <div style="background:#f9fafb;border:1px solid #e5e7eb;
                          border-radius:4px;padding:16px;margin:0 0 24px">
                <p style="margin:0 0 8px;color:#374151;font-size:12px">
                  <strong>Clave de acceso:</strong> {safe_access_key}
                </p>
                <p style="margin:0 0 8px;color:#374151;font-size:12px">
                  <strong>Número de autorización:</strong> {safe_auth_number}
                </p>
                <p style="margin:0;color:#374151;font-size:12px">
                  <strong>ID interno:</strong> {safe_document_id}
                </p>
              </div>

              <p style="margin:0;color:#888;font-size:13px;line-height:1.6">
                Puedes descargar el RIDE desde tu panel de Wali.
              </p>
            </td>
          </tr>

          <tr>
            <td style="background:#f8f9fa;padding:20px 40px;
                       border-top:1px solid #e9ecef">
              <p style="margin:0;color:#aaa;font-size:12px;text-align:center">
                © Wali · Ecuador
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _build_document_buyer_html(
    buyer_name: str,
    buyer_id: str,
    access_key: str,
    authorization_number: str,
    issuer_name: str,
    issuer_ruc: str,
    issued_at: str,
    authorized_at: str,
    total: str,
    currency: str,
) -> str:
    safe_name = escape(buyer_name or "cliente", quote=True)
    safe_buyer_id = escape(buyer_id, quote=True)
    safe_issuer = escape(issuer_name or "Emisor", quote=True)
    display_issued_at = _format_date(issued_at)
    display_authorized_at = _format_datetime(authorized_at)
    display_total = f"{total or '0.00'} {currency or 'USD'}"

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

          {_render_header("Documento tributario electrónico autorizado")}

          <tr>
            <td style="padding:40px">
              <h2 style="margin:0 0 16px;color:#0D1126;font-size:20px">
                Estimado(a): {safe_name} ({safe_buyer_id})
              </h2>
              <p style="margin:0 0 24px;color:#444;line-height:1.6">
                Adjunto encontrará el Documento Tributario Electrónico autorizado por el SRI.
              </p>

              <div style="background:#f8f9fa;border-left:4px solid #0D1126;
                          border-radius:4px;padding:20px;margin:0 0 24px">
                <p style="margin:0 0 10px;color:#0D1126;font-size:14px;font-weight:700">
                  Documento tributario electrónico
                </p>
                <table width="100%" cellpadding="0" cellspacing="0">
                  {_summary_row("Emitido por", f"{issuer_name or 'Emisor'} ({issuer_ruc})")}
                  {_summary_row("Tipo", "Factura")}
                  {_summary_row("Identificador", access_key)}
                  {_summary_row("Fecha de emisión", display_issued_at)}
                  {_summary_row("Fecha de autorización", display_authorized_at)}
                  {_summary_row("Número de autorización", authorization_number)}
                  {_summary_row("Total", display_total)}
                </table>
              </div>

              <p style="margin:0 0 18px;color:#444;line-height:1.6">
                Para nosotros es un placer servirle.
              </p>

              <div style="background:#f9fafb;border:1px solid #e5e7eb;
                          border-radius:4px;padding:16px;margin:0 0 24px">
                <p style="margin:0;color:#6b7280;font-size:12px;line-height:1.6">
                  <strong>Nota:</strong> Este correo electrónico ha sido enviado
                  automáticamente. Por favor no responda a esta dirección. Si requiere
                  cualquier aclaración o información adicional sobre la factura electrónica
                  debe comunicarse directamente con {safe_issuer}.
                </p>
              </div>

              <p style="margin:0;color:#888;font-size:13px;line-height:1.6">
                Se adjuntan el XML autorizado y el RIDE PDF. Consérvelos como respaldo
                tributario.
              </p>
            </td>
          </tr>

          <tr>
            <td style="background:#f8f9fa;padding:20px 40px;
                       border-top:1px solid #e9ecef">
              <p style="margin:0;color:#aaa;font-size:12px;text-align:center">
                © Wali · Ecuador
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _build_document_rejected_html(
    legal_rep_name: str, access_key: str, sri_errors: list[dict]
) -> str:
    safe_name = escape(legal_rep_name, quote=True)
    safe_access_key = escape(access_key, quote=True)
    errors_html = "".join(
        f'<p style="margin:0 0 6px;color:#0D1126;font-size:13px">'
        f"<strong>{escape(str(e.get('code', '')), quote=True)}:</strong> "
        f"{escape(str(e.get('user_message') or e.get('message', '')), quote=True)}</p>"
        for e in sri_errors
    )

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

          {_render_header(danger=True)}

          <tr>
            <td style="padding:40px">
              <h2 style="margin:0 0 16px;color:#0D1126;font-size:20px">
                Hola, {safe_name}
              </h2>
              <p style="margin:0 0 24px;color:#444;line-height:1.6">
                El SRI <strong>rechazó</strong> la factura con clave de acceso
                {safe_access_key}. Corrige los datos y vuelve a emitirla.
              </p>

              <div style="background:#fff1f2;border-left:4px solid #b91c1c;
                          border-radius:4px;padding:20px;margin:0 0 24px">
                {errors_html}
              </div>
            </td>
          </tr>

          <tr>
            <td style="background:#f8f9fa;padding:20px 40px;
                       border-top:1px solid #e9ecef">
              <p style="margin:0;color:#aaa;font-size:12px;text-align:center">
                © Wali · Ecuador
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _build_document_failed_permanent_html(legal_rep_name: str, access_key: str) -> str:
    safe_name = escape(legal_rep_name, quote=True)
    safe_access_key = escape(access_key, quote=True)

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

          {_render_header(danger=True)}

          <tr>
            <td style="padding:40px">
              <h2 style="margin:0 0 16px;color:#0D1126;font-size:20px">
                Hola, {safe_name}
              </h2>
              <p style="margin:0 0 24px;color:#444;line-height:1.6">
                No pudimos confirmar la autorización del SRI para la factura con
                clave de acceso <strong>{safe_access_key}</strong> tras varios
                intentos. Nuestro equipo revisará el caso — contáctanos si es urgente.
              </p>
            </td>
          </tr>

          <tr>
            <td style="background:#f8f9fa;padding:20px 40px;
                       border-top:1px solid #e9ecef">
              <p style="margin:0;color:#aaa;font-size:12px;text-align:center">
                © Wali · Ecuador
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
    def send_onboarding_otp(
        self,
        *,
        email: str,
        legal_rep_name: str,
        otp: str,
        expires_at: str,
    ) -> None:
        api_key = _get_api_key()
        payload = {
            "sender": {"name": _SENDER_NAME, "email": _SENDER_EMAIL},
            "to": [{"email": email, "name": legal_rep_name}],
            "subject": "Verifica tu correo — Wali",
            "htmlContent": _build_onboarding_otp_html(legal_rep_name, otp, expires_at),
        }
        _send(api_key, payload, log_email=email)

    def send_welcome(self, *, email: str, legal_rep_name: str, temp_password: str) -> None:
        api_key = _get_api_key()
        payload = {
            "sender": {"name": _SENDER_NAME, "email": _SENDER_EMAIL},
            "to": [{"email": email, "name": legal_rep_name}],
            "subject": "Bienvenido a Wali — tus credenciales de acceso",
            "htmlContent": _build_html(legal_rep_name, email, temp_password),
        }
        _send(api_key, payload, log_email=email)

    def send_enterprise_lead_notification(
        self,
        *,
        superadmin_email: str,
        trade_name: str,
        ruc: str,
        email: str,
        plan_id: str,
        plan_name: str = "",
    ) -> None:
        api_key = _get_api_key()
        payload = {
            "sender": {"name": _SENDER_NAME, "email": _SENDER_EMAIL},
            "to": [{"email": superadmin_email}],
            "subject": f"Nuevo lead Corporativo — {trade_name}",
            "htmlContent": _build_enterprise_lead_html(
                trade_name, ruc, email, plan_name or plan_id
            ),
        }
        _send(api_key, payload, log_email=superadmin_email)

    def send_certificate_expiry_alert(
        self,
        *,
        email: str,
        legal_rep_name: str,
        trade_name: str,
        ruc: str,
        cert_expires_at: str,
        days_remaining: int,
    ) -> None:
        api_key = _get_api_key()
        payload = {
            "sender": {"name": _SENDER_NAME, "email": _SENDER_EMAIL},
            "to": [{"email": email, "name": legal_rep_name}],
            "subject": f"Tu certificado digital vence en {days_remaining} días — Wali",
            "htmlContent": _build_certificate_expiry_alert_html(
                legal_rep_name, trade_name, ruc, cert_expires_at, days_remaining
            ),
        }
        _send(api_key, payload, log_email=email)

    def send_subscription_renewal_reminder(
        self,
        *,
        email: str,
        legal_rep_name: str,
        trade_name: str,
        plan_cycle_ends_at: str,
        days_remaining: int,
        renewal_url: str,
    ) -> None:
        api_key = _get_api_key()
        payload = {
            "sender": {"name": _SENDER_NAME, "email": _SENDER_EMAIL},
            "to": [{"email": email, "name": legal_rep_name}],
            "subject": f"Tu suscripción vence en {days_remaining} días — Wali",
            "htmlContent": _build_subscription_renewal_reminder_html(
                legal_rep_name, trade_name, plan_cycle_ends_at, days_remaining, renewal_url
            ),
        }
        _send(api_key, payload, log_email=email)

    def send_subscription_expired(
        self,
        *,
        email: str,
        legal_rep_name: str,
        trade_name: str,
        renewal_url: str,
    ) -> None:
        api_key = _get_api_key()
        payload = {
            "sender": {"name": _SENDER_NAME, "email": _SENDER_EMAIL},
            "to": [{"email": email, "name": legal_rep_name}],
            "subject": "Tu suscripción ha vencido — Wali",
            "htmlContent": _build_subscription_expired_html(
                legal_rep_name, trade_name, renewal_url
            ),
        }
        _send(api_key, payload, log_email=email)

    def send_payment_failed(
        self,
        *,
        email: str,
        legal_rep_name: str,
        trade_name: str,
        renewal_url: str,
    ) -> None:
        api_key = _get_api_key()
        payload = {
            "sender": {"name": _SENDER_NAME, "email": _SENDER_EMAIL},
            "to": [{"email": email, "name": legal_rep_name}],
            "subject": "Pago fallido — acción requerida para mantener tu cuenta activa",
            "htmlContent": _build_payment_failed_html(legal_rep_name, trade_name, renewal_url),
        }
        _send(api_key, payload, log_email=email)

    def send_document_authorized(
        self,
        *,
        email: str,
        legal_rep_name: str,
        document_id: str,
        access_key: str,
        authorization_number: str,
        issuer_name: str,
        issuer_ruc: str,
        buyer_name: str,
        buyer_id: str,
        buyer_email: str,
        sequential_display: str,
        issued_at: str,
        authorized_at: str,
        total: str,
        currency: str,
    ) -> None:
        api_key = _get_api_key()
        payload = {
            "sender": {"name": _SENDER_NAME, "email": _SENDER_EMAIL},
            "to": [{"email": email, "name": legal_rep_name}],
            "subject": "Tu factura fue autorizada por el SRI — Wali",
            "htmlContent": _build_document_authorized_html(
                legal_rep_name,
                document_id,
                access_key,
                authorization_number,
                issuer_name,
                issuer_ruc,
                buyer_name,
                buyer_id,
                buyer_email,
                sequential_display,
                issued_at,
                authorized_at,
                total,
                currency,
            ),
        }
        _send(api_key, payload, log_email=email)

    def send_document_rejected(
        self,
        *,
        email: str,
        legal_rep_name: str,
        document_id: str,
        access_key: str,
        sri_errors: list[dict],
    ) -> None:
        api_key = _get_api_key()
        payload = {
            "sender": {"name": _SENDER_NAME, "email": _SENDER_EMAIL},
            "to": [{"email": email, "name": legal_rep_name}],
            "subject": "El SRI rechazó tu factura — Wali",
            "htmlContent": _build_document_rejected_html(legal_rep_name, access_key, sri_errors),
        }
        _send(api_key, payload, log_email=email)

    def send_document_failed_permanent(
        self,
        *,
        email: str,
        legal_rep_name: str,
        document_id: str,
        access_key: str,
    ) -> None:
        api_key = _get_api_key()
        payload = {
            "sender": {"name": _SENDER_NAME, "email": _SENDER_EMAIL},
            "to": [{"email": email, "name": legal_rep_name}],
            "subject": "No pudimos confirmar tu factura con el SRI — Wali",
            "htmlContent": _build_document_failed_permanent_html(legal_rep_name, access_key),
        }
        _send(api_key, payload, log_email=email)

    def send_document_to_buyer(
        self,
        *,
        email: str,
        buyer_name: str,
        document_id: str,
        access_key: str,
        authorization_number: str,
        issuer_name: str,
        issuer_ruc: str,
        buyer_id: str,
        issued_at: str,
        authorized_at: str,
        total: str,
        currency: str,
        xml_content: bytes,
        xml_filename: str,
        ride_content: bytes,
        ride_filename: str,
    ) -> None:
        api_key = _get_api_key()
        payload = {
            "sender": {"name": _SENDER_NAME, "email": _SENDER_EMAIL},
            "to": [{"email": email, "name": buyer_name}],
            "subject": "Factura electrónica autorizada — XML y RIDE adjuntos",
            "htmlContent": _build_document_buyer_html(
                buyer_name,
                buyer_id,
                access_key,
                authorization_number,
                issuer_name,
                issuer_ruc,
                issued_at,
                authorized_at,
                total,
                currency,
            ),
            "attachment": [
                {
                    "name": xml_filename,
                    "content": base64.b64encode(xml_content).decode("ascii"),
                },
                {
                    "name": ride_filename,
                    "content": base64.b64encode(ride_content).decode("ascii"),
                },
            ],
        }
        _send(api_key, payload, log_email=email)

    def send_orphan_payment_alert(
        self,
        *,
        superadmin_email: str,
        order_id: str,
        payer_email: str | None,
        plan_id: str,
        amount: str,
        currency: str,
        confirmed_at: str,
    ) -> None:
        api_key = _get_api_key()
        payload = {
            "sender": {"name": _SENDER_NAME, "email": _SENDER_EMAIL},
            "to": [{"email": superadmin_email}],
            "subject": f"[ALERTA] Pago sin cuenta — {order_id}",
            "htmlContent": _build_orphan_payment_alert_html(
                order_id,
                payer_email or "desconocido",
                plan_id,
                amount,
                currency,
                confirmed_at,
            ),
        }
        _send(api_key, payload, log_email=superadmin_email)
