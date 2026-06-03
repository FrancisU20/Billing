"""
Servicio de gestión de certificados de firma electrónica.

Flujo de carga:
1. Frontend solicita presigned URL → backend genera URL temporal de S3
2. Frontend sube el .p12 directamente a S3 (nunca pasa por el backend)
3. Frontend confirma la carga con la contraseña del certificado
4. Backend descarga el .p12 de S3, valida y extrae metadatos con cryptography
5. Backend guarda la contraseña cifrada en Secrets Manager (cifrada por KMS)
6. Backend elimina el .p12 del bucket de uploads temporales
7. Backend registra el certificado en signing_certificates con el ARN del secret

El .p12 en sí NUNCA se guarda en Secrets Manager — solo la contraseña.
El archivo cifrado reside en S3 con clave KMS.
"""
import json

import boto3
from cryptography.hazmat.primitives.serialization import pkcs12

from app.shared.config import get_settings
from app.shared.logging import logger

settings = get_settings()


def generate_upload_url(tenant_id: str, cert_id: str, expires_in: int = 300) -> tuple[str, str]:
    """Genera una presigned URL de S3 para que el frontend suba el .p12 directamente."""
    s3 = boto3.client("s3", region_name=settings.env != "local" and "sa-east-1" or None)
    s3_key = f"tenants/{tenant_id}/certs/uploads/{cert_id}.p12"
    url = s3.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.s3_documents_bucket,
            "Key": s3_key,
            "ContentType": "application/x-pkcs12",
        },
        ExpiresIn=expires_in,
    )
    return url, s3_key


def validate_and_store_certificate(
    tenant_id: str,
    cert_id: str,
    s3_key_upload: str,
    password: str,
) -> dict:
    """
    Descarga el .p12, valida con cryptography, guarda contraseña en Secrets Manager,
    mueve el archivo a la ubicación permanente.
    Devuelve metadatos del certificado (fechas, titular).
    """
    s3 = boto3.client("s3")
    secrets = boto3.client("secretsmanager")

    # 1. Descargar .p12 temporal de S3
    response = s3.get_object(Bucket=settings.s3_documents_bucket, Key=s3_key_upload)
    p12_data = response["Body"].read()

    # 2. Validar certificado con cryptography — nunca loguear el contenido
    try:
        private_key, certificate, _ = pkcs12.load_key_and_certificates(
            p12_data, password.encode()
        )
    except Exception as exc:
        logger.warning("Certificate validation failed — removing temp upload",
                       extra={"error": type(exc).__name__, "s3_key": s3_key_upload})
        s3.delete_object(Bucket=settings.s3_documents_bucket, Key=s3_key_upload)
        raise ValueError("Contraseña incorrecta o certificado inválido") from exc

    if certificate is None:
        raise ValueError("El archivo no contiene un certificado válido")

    # 3. Extraer metadatos del certificado
    not_valid_before = certificate.not_valid_before_utc.date()
    not_valid_after = certificate.not_valid_after_utc.date()
    subject = certificate.subject.rfc4514_string()

    # 4. Mover .p12 a ubicación permanente (cifrado por KMS en el bucket)
    permanent_key = f"tenants/{tenant_id}/certs/{cert_id}.p12"
    s3.copy_object(
        Bucket=settings.s3_documents_bucket,
        CopySource={"Bucket": settings.s3_documents_bucket, "Key": s3_key_upload},
        Key=permanent_key,
    )
    s3.delete_object(Bucket=settings.s3_documents_bucket, Key=s3_key_upload)

    # 5. Guardar SOLO la contraseña en Secrets Manager (el .p12 permanece en S3)
    secret_name = f"codelabs-billing/{settings.env}/tenant/{tenant_id}/cert/{cert_id}"
    secret_value = json.dumps({"password": password, "s3_key": permanent_key})

    try:
        response = secrets.create_secret(
            Name=secret_name,
            SecretString=secret_value,
            Description=f"Contraseña del certificado de firma electrónica — tenant {tenant_id}",
        )
        secret_arn = response["ARN"]
    except secrets.exceptions.ResourceExistsException:
        response = secrets.put_secret_value(SecretId=secret_name, SecretString=secret_value)
        secret_arn = secrets.describe_secret(SecretId=secret_name)["ARN"]

    logger.info(
        "Certificate stored successfully",
        extra={"tenant_id": tenant_id, "cert_id": cert_id, "subject": subject},
    )

    return {
        "s3_key": permanent_key,
        "secrets_manager_arn": secret_arn,
        "fecha_emision": not_valid_before,
        "fecha_expiracion": not_valid_after,
        "subject": subject,
    }
