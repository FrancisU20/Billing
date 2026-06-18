from __future__ import annotations

"""Read authorized document files from S3 for email attachments."""

import boto3
from botocore.exceptions import ClientError

from lambdas.workers.email_notifications.ports import (
    DocumentAttachmentReader,
    DocumentAttachments,
)
from shared.errors import ExternalServiceError
from shared.logger import get_logger

_log = get_logger(__name__)


class S3DocumentAttachmentReader(DocumentAttachmentReader):
    def __init__(self, bucket_name: str, client=None) -> None:
        self._bucket_name = bucket_name
        self._client = client or boto3.client("s3")

    def get_authorized_document(
        self, *, xml_s3_key: str, ride_s3_key: str, document_id: str
    ) -> DocumentAttachments:
        try:
            xml_obj = self._client.get_object(Bucket=self._bucket_name, Key=xml_s3_key)
            ride_obj = self._client.get_object(Bucket=self._bucket_name, Key=ride_s3_key)
            xml_content = xml_obj["Body"].read()
            ride_content = ride_obj["Body"].read()
        except ClientError as exc:
            _log.error(
                "S3 get_object error loading document attachments",
                document_id=document_id,
                xml_s3_key=xml_s3_key,
                ride_s3_key=ride_s3_key,
            )
            raise ExternalServiceError("no se pudieron cargar los adjuntos del documento") from exc

        return DocumentAttachments(
            xml_content=xml_content,
            xml_filename=f"{document_id}.xml",
            ride_content=ride_content,
            ride_filename=f"{document_id}.pdf",
        )
