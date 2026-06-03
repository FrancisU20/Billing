import json

import boto3

from app.shared.config import get_settings

settings = get_settings()


def _sqs():
    return boto3.client("sqs")


def encolar_procesamiento(comprobante_id: str, tenant_id: str) -> None:
    """Encola un comprobante para procesamiento (FIFO — deduplicación por comprobante_id)."""
    _sqs().send_message(
        QueueUrl=settings.sqs_invoice_processing_url,
        MessageBody=json.dumps({"comprobante_id": comprobante_id, "tenant_id": tenant_id}),
        MessageGroupId=tenant_id,
        MessageDeduplicationId=comprobante_id,
    )


def encolar_consulta_autorizacion(comprobante_id: str, clave_acceso: str, ambiente: str) -> None:
    _sqs().send_message(
        QueueUrl=settings.sqs_sri_authorization_url,
        MessageBody=json.dumps({
            "comprobante_id": comprobante_id,
            "clave_acceso": clave_acceso,
            "ambiente": ambiente,
        }),
        MessageDeduplicationId=None,
    )


def encolar_envio_email(comprobante_id: str, tenant_id: str) -> None:
    _sqs().send_message(
        QueueUrl=settings.sqs_email_dispatch_url,
        MessageBody=json.dumps({"comprobante_id": comprobante_id, "tenant_id": tenant_id}),
    )


def encolar_importacion_lote(lote_id: str, tenant_id: str) -> None:
    _sqs().send_message(
        QueueUrl=settings.sqs_batch_import_url,
        MessageBody=json.dumps({"lote_id": lote_id, "tenant_id": tenant_id}),
    )
