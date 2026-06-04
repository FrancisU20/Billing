from datetime import UTC, datetime
from uuid import UUID

from aws_lambda_powertools import Logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums.ambiente_sri import AmbienteSri
from app.domain.enums.estado_comprobante import EstadoComprobante
from app.infrastructure.database.connection import get_session_factory
from app.infrastructure.database.models.email import EmailDispatchModel
from app.infrastructure.database.repositories.comprobante_repository import SqlAlchemyComprobanteRepository
from app.infrastructure.database.repositories.tenant_repository import SqlAlchemyTenantRepository
from app.infrastructure.email.dispatcher import dispatch
from app.infrastructure.email.provider import EmailMessage
from app.infrastructure.pdf.ride_generator import generar_ride_factura
from app.infrastructure.storage.s3_storage import descargar_documento, s3_key_pdf, subir_documento

logger = Logger(service="codelabs-billing-email-dispatch")


async def enviar_bienvenida_tenant(email: str, razon_social: str, temp_password: str) -> None:
    """Envía el email de bienvenida al admin de un tenant recién creado."""
    from app.infrastructure.email.brevo_provider import BrevoEmailProvider
    from app.shared.config import get_settings

    settings = get_settings()
    credentials = settings.get_email_credentials()
    smtp_user = credentials.get("smtp_user")
    smtp_password = credentials.get("smtp_password")

    if not smtp_user or not smtp_password:
        logger.warning("SMTP credentials not configured — skipping welcome email")
        return

    provider = BrevoEmailProvider(smtp_user=smtp_user, smtp_password=smtp_password)
    provider.send(EmailMessage(
        to=email,
        subject="Bienvenido a CodeLabs Billing — Tus credenciales de acceso",
        html_body=_welcome_email_html(razon_social, email, temp_password),
        from_name="CodeLabs Billing",
        from_email="noreply@codelabsecuador.com",
        attachments=[],
    ))
    logger.info("Welcome email sent", extra={"email": email})


def _welcome_email_html(razon_social: str, email: str, password: str) -> str:
    return f"""
    <html><body style="font-family:Arial,sans-serif;color:#333;max-width:600px;margin:auto">
      <h2 style="color:#1a56db">Bienvenido a CodeLabs Billing</h2>
      <p>Hola, tu empresa <strong>{razon_social}</strong> ha sido registrada en CodeLabs Billing Cloud.</p>
      <p>Tus credenciales de acceso son:</p>
      <table style="border-collapse:collapse;width:100%;margin:16px 0">
        <tr style="background:#f3f4f6">
          <td style="padding:10px;font-weight:bold;width:140px">Correo</td>
          <td style="padding:10px;font-family:monospace">{email}</td>
        </tr>
        <tr>
          <td style="padding:10px;font-weight:bold">Contraseña</td>
          <td style="padding:10px;font-family:monospace;font-size:16px">{password}</td>
        </tr>
      </table>
      <p>Accede en: <a href="https://billing-dev.codelabsecuador.com">billing-dev.codelabsecuador.com</a></p>
      <p style="color:#666;font-size:12px">Te recomendamos cambiar tu contraseña en la primera sesión.</p>
      <hr style="border:none;border-top:1px solid #e5e7eb;margin:24px 0">
      <p style="color:#999;font-size:11px">CodeLabs Billing Cloud — Sistema de Facturación Electrónica Ecuador</p>
    </body></html>
    """


async def enviar_comprobante_email(comprobante_id: str, tenant_id: str) -> None:
    async with get_session_factory()() as session, session.begin():
        await _enviar(session, comprobante_id, tenant_id)


async def _enviar(session: AsyncSession, comprobante_id: str, tenant_id: str) -> None:
    comp_repo = SqlAlchemyComprobanteRepository(session)
    tenant_repo = SqlAlchemyTenantRepository(session)

    comp = await comp_repo.get_by_id(UUID(comprobante_id), UUID(tenant_id))
    tenant = await tenant_repo.get_by_id(UUID(tenant_id))

    if not comp or not tenant:
        logger.error("Comprobante o tenant no encontrado")
        return

    # Idempotency: si ya existe un dispatch exitoso, no reenviar
    existing = await session.execute(
        select(EmailDispatchModel).where(
            EmailDispatchModel.comprobante_id == comp.id,
            EmailDispatchModel.tipo == "RECEPTOR",
            EmailDispatchModel.estado == "SENT",
        )
    )
    if existing.scalar_one_or_none():
        logger.info("Email ya enviado — skip", extra={"comprobante_id": comprobante_id})
        return

    email_receptor = comp.datos.get("email_comprador")
    if not email_receptor:
        logger.info("Sin email receptor — registrando SKIPPED", extra={"comprobante_id": comprobante_id})
        skip_record = EmailDispatchModel(
            comprobante_id=comp.id,
            destinatario="",
            tipo="RECEPTOR",
            estado="SKIPPED",
            intentos=0,
        )
        session.add(skip_record)
        await comp_repo.update_estado(comp.id, EstadoComprobante.EMAIL_SENT)
        return

    # Generar o descargar PDF
    if not comp.s3_key_pdf:
        datos_tenant = {
            "ruc": tenant.ruc,
            "razon_social": tenant.razon_social,
            "nombre_comercial": tenant.nombre_comercial,
        }
        pdf_bytes = generar_ride_factura(
            datos_comprobante={
                "clave_acceso": comp.clave_acceso,
                "numero_autorizacion": comp.numero_autorizacion,
                "fecha_autorizacion": str(comp.fecha_autorizacion or ""),
                "establecimiento": comp.establecimiento,
                "punto_emision": comp.punto_emision,
                "secuencial": comp.secuencial,
                "datos": comp.datos,
                "ambiente": "1" if tenant.ambiente_sri == AmbienteSri.PRUEBAS else "2",
            },
            datos_tenant=datos_tenant,
        )
        s3_key = s3_key_pdf(tenant_id, comp.clave_acceso or comprobante_id)
        subir_documento(pdf_bytes, s3_key, "application/pdf")
        comp.s3_key_pdf = s3_key
        await session.flush()
    else:
        pdf_bytes = descargar_documento(comp.s3_key_pdf)

    xml_bytes = b""
    if comp.s3_key_xml_autorizado:
        xml_bytes = descargar_documento(comp.s3_key_xml_autorizado)

    numero = f"{comp.establecimiento}-{comp.punto_emision}-{comp.secuencial}"
    message = EmailMessage(
        to=email_receptor,
        subject=f"Factura electrónica {numero} - {tenant.razon_social}",
        html_body=_html_template(tenant.razon_social, numero, comp.clave_acceso or ""),
        attachments=[
            {"filename": f"factura_{numero}.pdf", "content": pdf_bytes, "content_type": "application/pdf"},
            *([{"filename": f"factura_{numero}.xml", "content": xml_bytes, "content_type": "application/xml"}]
              if xml_bytes else []),
        ],
        from_name=tenant.nombre_comercial or tenant.razon_social,
    )

    dispatch_model = EmailDispatchModel(
        comprobante_id=comp.id,
        destinatario=email_receptor,
        tipo="RECEPTOR",
        estado="PENDING",
        intentos=0,
    )
    session.add(dispatch_model)

    try:
        proveedor = dispatch(message)
        dispatch_model.estado = "SENT"
        dispatch_model.proveedor = proveedor
        dispatch_model.enviado_at = datetime.now(UTC)
        dispatch_model.intentos = 1
        await comp_repo.update_estado(comp.id, EstadoComprobante.EMAIL_SENT)
    except ValueError as e:
        dispatch_model.estado = "FAILED"
        dispatch_model.error_detalle = str(e)
        dispatch_model.intentos = 1
        await comp_repo.update_estado(comp.id, EstadoComprobante.EMAIL_FAILED)
        logger.error("Email dispatch failed", extra={"error": str(e)})


def _html_template(razon_social: str, numero: str, clave_acceso: str) -> str:
    return f"""
    <html><body style="font-family:Arial,sans-serif;color:#333;max-width:600px;margin:auto">
      <h2 style="color:#1a56db">Factura Electrónica</h2>
      <p>Estimado cliente,</p>
      <p>Adjunto encontrará su <strong>Factura Electrónica No. {numero}</strong>
         emitida por <strong>{razon_social}</strong>, autorizada por el SRI.</p>
      <table style="border-collapse:collapse;width:100%;margin:16px 0">
        <tr style="background:#f3f4f6">
          <td style="padding:8px;font-weight:bold">Número:</td>
          <td style="padding:8px">{numero}</td>
        </tr>
        <tr>
          <td style="padding:8px;font-weight:bold">Clave de acceso:</td>
          <td style="padding:8px;font-size:11px;font-family:monospace">{clave_acceso}</td>
        </tr>
      </table>
      <p style="color:#666;font-size:12px">
        Puede verificar la autenticidad de este documento en
        <a href="https://srienlinea.sri.gob.ec">SRI en Línea</a>.
      </p>
      <hr style="border:none;border-top:1px solid #e5e7eb">
      <p style="color:#999;font-size:11px">
        Este es un mensaje automático generado por CodeLabs Billing Cloud.
      </p>
    </body></html>
    """
