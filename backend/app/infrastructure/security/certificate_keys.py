from app.shared.config import get_settings

settings = get_settings()


def certificate_upload_key(tenant_id: str, cert_id: str) -> str:
    return f"tenants/{tenant_id}/certs/uploads/{cert_id}.p12"


def certificate_storage_key(tenant_id: str, cert_id: str) -> str:
    return f"tenants/{tenant_id}/certs/{cert_id}.p12"


def certificate_secret_name(tenant_id: str, cert_id: str) -> str:
    return f"codelabs-billing/{settings.env}/tenant/{tenant_id}/cert/{cert_id}"
