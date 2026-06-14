from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CertificateMetadata:
    subject_ruc: str
    expires_at: datetime
    issuer: str
