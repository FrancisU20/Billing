from __future__ import annotations

import boto3

from lambdas.documents.domain.commands import GetXmlUrlCommand
from lambdas.documents.domain.errors import XmlNotAvailableError
from lambdas.documents.domain.repositories.i_documents_repository import IDocumentsRepository

_XML_URL_TTL_SECONDS = 900  # 15 minutes


class GetXmlUrlUseCase:
    def __init__(self, repo: IDocumentsRepository) -> None:
        self._repo = repo

    def execute(self, cmd: GetXmlUrlCommand) -> str:
        document = self._repo.get(cmd.tenant_id, cmd.document_id)

        if document.xml_s3_key is None:
            raise XmlNotAvailableError()

        s3 = boto3.client("s3")
        url: str = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": cmd.documents_bucket, "Key": document.xml_s3_key},
            ExpiresIn=_XML_URL_TTL_SECONDS,
        )
        return url
