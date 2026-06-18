from __future__ import annotations

import boto3

from lambdas.documents.domain.commands import GetRideUrlCommand
from lambdas.documents.domain.errors import RideNotAvailableError
from lambdas.documents.domain.repositories.i_documents_repository import IDocumentsRepository

_RIDE_URL_TTL_SECONDS = 900  # 15 minutes


class GetRideUrlUseCase:
    def __init__(self, repo: IDocumentsRepository) -> None:
        self._repo = repo

    def execute(self, cmd: GetRideUrlCommand) -> str:
        document = self._repo.get(cmd.tenant_id, cmd.document_id)

        if document.ride_s3_key is None:
            raise RideNotAvailableError()

        s3 = boto3.client("s3")
        url: str = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": cmd.documents_bucket, "Key": document.ride_s3_key},
            ExpiresIn=_RIDE_URL_TTL_SECONDS,
        )
        return url
