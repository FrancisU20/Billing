"""
Worker de procesamiento de comprobantes individuales.

Flujo:
1. Cargar comprobante de DB (debe estar en estado QUEUED)
2. Descargar XML firmado de S3
3. Enviar al SRI (recepción)
4. Si RECIBIDA → encolar para consulta de autorización
5. Si DEVUELTA → estado RETURNED_BY_SRI (no reintento automático)
6. Si error transitorio → estado RETRY_PENDING
"""
import hashlib
from datetime import datetime
from uuid import UUID

from aws_lambda_powertools import Logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums.ambiente_sri import AmbienteSri
from app.domain.enums.estado_comprobante import EstadoComprobante
from app.domain.schemas.factura import DatosFactura
from app.domain.value_objects.clave_acceso import ClaveAcceso
from app.infrastructure.database.connection import get_session_factory
from app.infrastructure.database.models.comprobante import SriSubmissionModel
from app.infrastructure.database.repositories.certificate_repository import CertificateRepository
from app.infrastructure.database.repositories.comprobante_repository import SqlAlchemyComprobanteRepository
from app.infrastructure.database.repositories.tenant_repository import SqlAlchemyTenantRepository
from app.infrastructure.queues.sqs_publisher import encolar_consulta_autorizacion
from app.infrastructure.sri.certificate_loader import cargar_p12
from app.infrastructure.sri.soap_client import enviar_comprobante
from app.infrastructure.sri.xml_generator import generar_factura
from app.infrastructure.sri.xml_signer import firmar_xml
from app.infrastructure.sri.xsd_validator import validar_xml
from app.infrastructure.storage.s3_storage import (
    descargar_documento,
    s3_key_xml_firmado,
    subir_documento,
)
from app.shared.config import get_settings

logger = Logger(service="codelabs-billing-invoice-worker")


async def procesar_comprobante(comprobante_id: str, tenant_id: str) -> None:
    async with get_session_factory()() as session, session.begin():
        await _procesar(session, comprobante_id, tenant_id)


async def _procesar(session: AsyncSession, comprobante_id: str, tenant_id: str) -> None:
    comp_repo = SqlAlchemyComprobanteRepository(session)
    tenant_repo = SqlAlchemyTenantRepository(session)

    comp = await comp_repo.get_by_id(UUID(comprobante_id), UUID(tenant_id))
    if not comp:
        logger.error("Comprobante no encontrado", extra={"comprobante_id": comprobante_id})
        return

    if comp.estado not in (EstadoComprobante.QUEUED, EstadoComprobante.RETRY_PENDING):
        logger.warning("Comprobante en estado incorrecto", extra={"estado": comp.estado})
        return

    tenant = await tenant_repo.get_by_id(UUID(tenant_id))
    if not tenant:
        logger.error("Tenant no encontrado", extra={"tenant_id": tenant_id})
        return

    # Ambiente efectivo — dev/staging siempre usan PRUEBAS
    # La regla está centralizada en Settings.effective_ambiente()
    settings = get_settings()
    ambiente = settings.effective_ambiente(tenant.ambiente_sri)

    try:
        # Paso 1: generar XML si no existe ya
        if not comp.s3_key_xml_firmado:
            await comp_repo.update_estado(comp.id, EstadoComprobante.PROCESSING)

            datos = DatosFactura(**comp.datos)

            # Generar clave de acceso
            # cod_numerico derivado del ID del comprobante — determinístico para
            # que reintentos produzcan la misma clave_acceso, evitando duplicados en el SRI.
            fecha = datetime.strptime(datos.fecha_emision, "%d/%m/%Y").date()
            cod_numerico = str(
                int(hashlib.sha256(str(comp.id).encode()).hexdigest()[:8], 16) % 90_000_000 + 10_000_000
            )
            clave = ClaveAcceso.generate(
                fecha_emision=fecha,
                tipo_comprobante=comp.tipo,
                ruc=tenant.ruc,
                ambiente="1" if ambiente == AmbienteSri.PRUEBAS else "2",
                establecimiento=comp.establecimiento,
                punto_emision=comp.punto_emision,
                secuencial=comp.secuencial or "000000001",
                codigo_numerico=cod_numerico,
            )

            xml = generar_factura(
                datos=datos,
                clave_acceso=clave,
                ruc_emisor=tenant.ruc,
                razon_social_emisor=tenant.razon_social,
                nombre_comercial_emisor=tenant.nombre_comercial or tenant.razon_social,
                dir_matriz_emisor=datos.direccion_establecimiento,
                establecimiento=comp.establecimiento,
                punto_emision=comp.punto_emision,
                secuencial=comp.secuencial or "000000001",
                ambiente="1" if ambiente == AmbienteSri.PRUEBAS else "2",
            )
            await comp_repo.update_estado(comp.id, EstadoComprobante.XML_GENERATED)

            # Validar XSD
            errores = validar_xml(xml, comp.tipo)
            if errores:
                logger.warning("XML no pasa validación XSD", extra={"errors": errores[:3]})
                await comp_repo.update_estado(
                    comp.id, EstadoComprobante.VALIDATION_FAILED,
                    metadata={"xsd_errors": errores},
                )
                return

            # Cargar certificado y firmar
            cert_repo = CertificateRepository(session)
            cert = await cert_repo.get_active_for_tenant(UUID(tenant_id))
            if not cert:
                await comp_repo.update_estado(
                    comp.id, EstadoComprobante.FAILED,
                    metadata={"error": "No hay certificado activo para este tenant"},
                )
                return

            p12_bytes, password = cargar_p12(tenant_id, str(cert.id))
            xml_firmado = firmar_xml(xml, p12_bytes, password)
            await comp_repo.update_estado(comp.id, EstadoComprobante.XML_SIGNED)

            # Subir XML firmado a S3
            s3_key = s3_key_xml_firmado(tenant_id, str(clave))
            subir_documento(xml_firmado, s3_key)

            # Actualizar comprobante con clave y s3_key
            comp.clave_acceso = str(clave)
            comp.s3_key_xml_firmado = s3_key
            await session.flush()
        else:
            # XML ya existe, descargar de S3
            xml_firmado = descargar_documento(comp.s3_key_xml_firmado).decode("utf-8")

        # Paso 2: enviar al SRI
        await comp_repo.update_estado(comp.id, EstadoComprobante.SENT_TO_SRI)
        respuesta = enviar_comprobante(xml_firmado, ambiente)

        logger.info("Respuesta SRI recepción", extra={
            "comprobante_id": comprobante_id,
            "estado": respuesta.estado,
        })

        # Registrar submission en DB
        submission = SriSubmissionModel(
            comprobante_id=comp.id,
            tipo="RECEPCION",
            ambiente=ambiente,
            request_claveacceso=comp.clave_acceso,
            response_estado=respuesta.estado,
            response_mensajes={"comprobantes": respuesta.comprobantes},
        )
        session.add(submission)

        if respuesta.estado == "RECIBIDA":
            await comp_repo.update_estado(comp.id, EstadoComprobante.RECEIVED_BY_SRI)
            await comp_repo.update_estado(comp.id, EstadoComprobante.PENDING_AUTHORIZATION)
            await session.flush()
            encolar_consulta_autorizacion(comprobante_id, comp.clave_acceso or "", ambiente)
        elif respuesta.estado == "DEVUELTA":
            mensajes = [m["mensaje"] for c in respuesta.comprobantes for m in c.get("mensajes", [])]
            await comp_repo.update_estado(
                comp.id, EstadoComprobante.RETURNED_BY_SRI,
                metadata={"mensajes": mensajes},
            )
        else:
            comp.increment_retry()
            await comp_repo.update_estado(comp.id, EstadoComprobante.RETRY_PENDING)

    except Exception as e:
        logger.exception("Error procesando comprobante", extra={"comprobante_id": comprobante_id})
        await comp_repo.update_estado(
            comp.id, EstadoComprobante.FAILED,
            metadata={"error": str(e)},
        )
