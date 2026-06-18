from __future__ import annotations

"""
Loads and caches the tenant's p12 certificate (private key + X.509 cert) for
XAdES-BES signing.

Cached at module level, keyed by `secret_arn` — the Lambda container reuses the
loaded certificate across invocations (cold start loads it once, matches the
caching strategy documented in `context/INVOICES.md`). Zero Secrets Manager calls
per document after the first one in a given container.
"""

import base64

from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509 import Certificate

from shared.errors import ExternalServiceError
from shared.logger import get_logger
from shared.secrets.client import get_secret_json

_log = get_logger(__name__)

_cache: dict[str, tuple[RSAPrivateKey, Certificate]] = {}


def load_certificate(secret_arn: str) -> tuple[RSAPrivateKey, Certificate]:
    if secret_arn in _cache:
        return _cache[secret_arn]

    secret = get_secret_json(secret_arn)
    p12_bytes = base64.b64decode(secret["p12_b64"])
    password = secret["password"]

    private_key, certificate, _ = pkcs12.load_key_and_certificates(
        p12_bytes, password.encode("utf-8")
    )
    if private_key is None or certificate is None:
        _log.error("certificate secret has no private key or certificate", secret_arn=secret_arn)
        raise ExternalServiceError("certificado del tenant inválido")

    _cache[secret_arn] = (private_key, certificate)
    return private_key, certificate
