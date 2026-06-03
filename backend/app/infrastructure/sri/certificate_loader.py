"""
Carga el certificado p12 desde S3 y su contraseña desde Secrets Manager.
Se llama desde los workers — nunca desde la API.
"""
import json

import boto3

from app.shared.config import get_settings

settings = get_settings()


def cargar_p12(tenant_id: str, cert_id: str) -> tuple[bytes, str]:
    """
    Retorna (p12_bytes, password) para un certificado de tenant.
    El .p12 está en S3 cifrado con KMS.
    La contraseña está en Secrets Manager.
    """
    secret_name = f"codelabs-billing/{settings.env}/tenant/{tenant_id}/cert/{cert_id}"

    secrets = boto3.client("secretsmanager")
    response = secrets.get_secret_value(SecretId=secret_name)
    secret_data = json.loads(response["SecretString"])

    password = secret_data["password"]
    s3_key = secret_data["s3_key"]

    s3 = boto3.client("s3")
    obj = s3.get_object(Bucket=settings.s3_documents_bucket, Key=s3_key)
    p12_bytes = obj["Body"].read()

    return p12_bytes, password
