from __future__ import annotations

from pydantic import BaseModel, Field


class CertificateUpdateRequest(BaseModel):
    certificate_b64: str = Field(..., min_length=1)
    cert_password: str = Field(..., min_length=1, max_length=200)
