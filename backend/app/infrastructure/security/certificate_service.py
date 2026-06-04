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
from botocore.config import Config as BotocoreConfig
from botocore.exceptions import ClientError
from cryptography.hazmat.primitives.serialization import pkcs12

from app.infrastructure.security.certificate_keys import (
    certificate_secret_name,
    certificate_storage_key,
    certificate_upload_key,
)
from app.shared.config import get_settings
from app.shared.logging import logger

settings = get_settings()


class CertificateValidationError(ValueError):
    """El archivo o la contrasena no permiten cargar un certificado valido."""


class CertificatePersistenceError(RuntimeError):
    """Error de infraestructura al persistir el certificado validado."""


def generate_upload_url(tenant_id: str, cert_id: str, expires_in: int = 300) -> tuple[str, str]:
    """Genera una presigned URL de S3 para que el frontend suba el .p12 directamente."""
    # SigV4 obligatorio: el bucket usa KMS y AWS requiere Signature Version 4 para KMS.
    s3 = boto3.client(
        "s3",
        region_name="sa-east-1" if settings.env != "local" else None,
        config=BotocoreConfig(signature_version="s3v4"),
    )
    s3_key = certificate_upload_key(tenant_id, cert_id)
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
    password: str,
) -> dict:
    """
    Descarga el .p12, valida con cryptography, guarda contraseña en Secrets Manager,
    mueve el archivo a la ubicación permanente.
    Devuelve metadatos del certificado (fechas, titular).
    """
    s3 = boto3.client("s3")
    secrets = boto3.client("secretsmanager")
    s3_key_upload = certificate_upload_key(tenant_id, cert_id)

    # 1. Descargar .p12 temporal de S3
    try:
        response = s3.get_object(Bucket=settings.s3_documents_bucket, Key=s3_key_upload)
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code in {"NoSuchKey", "NoSuchBucket", "404", "NotFound"}:
            raise CertificateValidationError(
                "No se encontro el archivo temporal del certificado. Vuelve a cargarlo."
            ) from exc
        logger.exception(
            "Certificate upload read failed",
            extra={"tenant_id": tenant_id, "cert_id": cert_id, "s3_key": s3_key_upload},
        )
        raise CertificatePersistenceError("No se pudo leer el certificado cargado") from exc

    p12_data = response["Body"].read()

    # 2. Validar certificado con cryptography — nunca loguear el contenido
    try:
        _private_key, certificate, _ = pkcs12.load_key_and_certificates(
            p12_data, password.encode()
        )
    except Exception as exc:
        logger.warning("Certificate validation failed — removing temp upload",
                       extra={"error": type(exc).__name__, "s3_key": s3_key_upload})
        _delete_temp_upload(s3, s3_key_upload)
        raise CertificateValidationError("Contraseña incorrecta o certificado inválido") from exc

    if certificate is None:
        _delete_temp_upload(s3, s3_key_upload)
        raise CertificateValidationError("El archivo no contiene un certificado válido")

    # 3. Extraer metadatos del certificado
    not_valid_before = certificate.not_valid_before_utc.date()
    not_valid_after = certificate.not_valid_after_utc.date()
    subject = certificate.subject.rfc4514_string()

    # 4. Mover .p12 a ubicación permanente (cifrado por KMS en el bucket)
    permanent_key = certificate_storage_key(tenant_id, cert_id)
    try:
        s3.copy_object(
            Bucket=settings.s3_documents_bucket,
            CopySource={"Bucket": settings.s3_documents_bucket, "Key": s3_key_upload},
            Key=permanent_key,
        )
    except ClientError as exc:
        logger.exception(
            "Certificate persistence to S3 failed",
            extra={"tenant_id": tenant_id, "cert_id": cert_id, "s3_key": s3_key_upload},
        )
        raise CertificatePersistenceError("No se pudo guardar el certificado validado") from exc

    # 5. Guardar SOLO la contraseña en Secrets Manager (el .p12 permanece en S3)
    secret_name = certificate_secret_name(tenant_id, cert_id)
    secret_value = json.dumps({"password": password, "s3_key": permanent_key})
    try:
        secret_arn = _store_certificate_secret(secrets, secret_name, secret_value, tenant_id)
    except CertificatePersistenceError:
        _delete_object(s3, permanent_key, "permanent certificate")
        raise

    _delete_temp_upload(s3, s3_key_upload)

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


def _delete_temp_upload(s3, s3_key_upload: str) -> None:
    _delete_object(s3, s3_key_upload, "temporary certificate upload")


def _delete_object(s3, s3_key: str, description: str) -> None:
    try:
        s3.delete_object(Bucket=settings.s3_documents_bucket, Key=s3_key)
    except ClientError:
        logger.warning("Could not remove %s", description, extra={"s3_key": s3_key})


def _store_certificate_secret(secrets, secret_name: str, secret_value: str, tenant_id: str) -> str:
    create_secret_kwargs = {
        "Name": secret_name,
        "SecretString": secret_value,
        "Description": f"Contraseña del certificado de firma electrónica — tenant {tenant_id}",
    }
    if settings.certificate_secrets_kms_key_arn:
        create_secret_kwargs["KmsKeyId"] = settings.certificate_secrets_kms_key_arn

    try:
        response = secrets.create_secret(**create_secret_kwargs)
        return response["ARN"]
    except secrets.exceptions.ResourceExistsException:
        try:
            secrets.put_secret_value(SecretId=secret_name, SecretString=secret_value)
            return secrets.describe_secret(SecretId=secret_name)["ARN"]
        except ClientError as exc:
            logger.exception("Certificate secret update failed", extra={"secret_name": secret_name})
            raise CertificatePersistenceError("No se pudo actualizar la contraseña del certificado") from exc
    except ClientError as exc:
        logger.exception("Certificate secret creation failed", extra={"secret_name": secret_name})
        raise CertificatePersistenceError("No se pudo guardar la contraseña del certificado") from exc
