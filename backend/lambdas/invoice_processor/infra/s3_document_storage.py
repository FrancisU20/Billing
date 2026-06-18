from __future__ import annotations

"""S3 storage for authorized documents — XML firmado + RIDE, ambos con LegalHold=ON.

Object Lock (WORM) ya está habilitado en el bucket (`StorageStack`); LegalHold=ON
por objeto es lo que realmente impide borrar/sobrescribir durante los 7 años de
retención legal (el default retention de gobernanza solo aplica en prod).
"""

import boto3
from botocore.exceptions import ClientError

from lambdas.invoice_processor.ports import IDocumentStorage
from shared.errors import ExternalServiceError
from shared.logger import get_logger

_log = get_logger(__name__)


class S3DocumentStorage(IDocumentStorage):
    def __init__(self, bucket_name: str, client=None) -> None:
        self._bucket_name = bucket_name
        self._client = client or boto3.client("s3")

    def put_authorized_document(
        self,
        *,
        tenant_id: str,
        document_id: str,
        year: int,
        signed_xml: str,
        ride_pdf: bytes,
    ) -> tuple[str, str]:
        xml_key = f"tenants/{tenant_id}/docs/{year}/{document_id}.xml"
        ride_key = f"tenants/{tenant_id}/docs/{year}/{document_id}.pdf"

        try:
            self._client.put_object(
                Bucket=self._bucket_name,
                Key=xml_key,
                Body=signed_xml.encode("utf-8"),
                ContentType="application/xml",
                ObjectLockLegalHoldStatus="ON",
            )
            self._client.put_object(
                Bucket=self._bucket_name,
                Key=ride_key,
                Body=ride_pdf,
                ContentType="application/pdf",
                ObjectLockLegalHoldStatus="ON",
            )
        except ClientError as exc:
            _log.error("S3 put_object error storing authorized document", document_id=document_id)
            raise ExternalServiceError("no se pudo guardar el documento autorizado") from exc

        return xml_key, ride_key
