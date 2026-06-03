import boto3

from app.shared.config import get_settings

settings = get_settings()


def _s3():
    return boto3.client("s3")


def subir_documento(contenido: bytes | str, s3_key: str, content_type: str = "application/xml") -> str:
    """Sube un documento a S3 y retorna la clave S3."""
    body = contenido.encode("utf-8") if isinstance(contenido, str) else contenido
    _s3().put_object(
        Bucket=settings.s3_documents_bucket,
        Key=s3_key,
        Body=body,
        ContentType=content_type,
    )
    return s3_key


def descargar_documento(s3_key: str) -> bytes:
    """Descarga un documento de S3."""
    response = _s3().get_object(Bucket=settings.s3_documents_bucket, Key=s3_key)
    return response["Body"].read()


def generar_presigned_url(s3_key: str, expires_in: int = 900) -> str:
    """Genera una URL prefirmada para descarga (TTL: 15 min por defecto)."""
    return _s3().generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.s3_documents_bucket, "Key": s3_key},
        ExpiresIn=expires_in,
    )


def s3_key_xml_firmado(tenant_id: str, clave_acceso: str) -> str:
    return f"tenants/{tenant_id}/xml/firmado/{clave_acceso[:4]}/{clave_acceso}.xml"


def s3_key_xml_autorizado(tenant_id: str, clave_acceso: str) -> str:
    return f"tenants/{tenant_id}/xml/autorizado/{clave_acceso[:4]}/{clave_acceso}.xml"


def s3_key_pdf(tenant_id: str, clave_acceso: str) -> str:
    return f"tenants/{tenant_id}/pdf/{clave_acceso[:4]}/{clave_acceso}.pdf"
