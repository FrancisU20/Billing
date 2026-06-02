import json
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env.local", env_file_encoding="utf-8", extra="ignore")

    # Ambiente
    env: str = Field(default="dev")

    # DB — host y nombre vienen como env vars (no sensibles)
    db_host: str = Field(default="localhost")
    db_port: int = Field(default=5432)
    db_name: str = Field(default="codelabs_billing")
    db_secret_arn: str = Field(default="")

    # S3
    s3_documents_bucket: str = Field(default="")
    s3_assets_bucket: str = Field(default="")
    s3_batches_bucket: str = Field(default="")

    # SQS
    sqs_invoice_processing_url: str = Field(default="")
    sqs_sri_authorization_url: str = Field(default="")
    sqs_email_dispatch_url: str = Field(default="")
    sqs_batch_import_url: str = Field(default="")

    # Cognito
    cognito_user_pool_id: str = Field(default="")
    cognito_web_client_id: str = Field(default="")

    # CORS
    cors_origins: list[str] = Field(default=["*"])

    # Nombre del secret en Secrets Manager para el email provider
    email_secret_name: str = Field(default="")

    @property
    def is_local(self) -> bool:
        return self.env == "local"

    def get_db_password(self) -> str:
        if self.is_local:
            import os
            return os.environ.get("DB_PASSWORD", "postgres")
        return _load_secret(self.db_secret_arn)["password"]

    def get_email_credentials(self) -> dict:
        if self.is_local or not self.email_secret_name:
            return {}
        return _load_secret(self.email_secret_name)


def _load_secret(secret_arn: str) -> dict:
    # Lambda Powertools cachea 5 minutos — ideal para evitar llamadas por cada invocación
    try:
        from aws_lambda_powertools.utilities import parameters
        value = parameters.get_secret(secret_arn)
        return json.loads(value) if isinstance(value, str) else value
    except Exception:
        import boto3
        client = boto3.client("secretsmanager")
        response = client.get_secret_value(SecretId=secret_arn)
        return json.loads(response["SecretString"])


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
