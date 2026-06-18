"""
StorageStack — S3 buckets con retención legal.

DocumentsBucket:
  - Object Lock (WORM) para cumplir la obligación de retención de 7 años del SRI Ecuador
    (Art. 41 Reglamento de Comprobantes de Venta). Guarda XMLs firmados y RIDEs (PDFs).
  - Default retention GOVERNANCE activa solo en prod; dev/staging sin default retention
    para que los objetos sean borrables manualmente durante pruebas.
  - Lifecycle: Standard → S3-IA @30d → Glacier Instant Retrieval @90d (optimiza costo de
    archivos maduros). Para un enterprise de 10,000 docs/día, baja de ~$35/mes a ~$8/mes.
  - Block public access total; RemovalPolicy.RETAIN siempre — datos legales, nunca destruir.
"""
from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_s3 as s3,
)
from constructs import Construct


class StorageStack(Stack):
    def __init__(
        self,
        scope:        Construct,
        construct_id: str,
        config:       dict,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        env     = config["env"]
        is_prod = env == "prod"

        # ── Documents Bucket ──────────────────────────────────────────────────
        # En prod: default retention GOVERNANCE 7 años aplica a cada objeto al escribirse.
        # En dev/staging: Object Lock habilitado (bucket es WORM-capable) pero sin default
        # retention; el invoice_processor pone LegalHold=ON por objeto al autorizar.
        default_retention = (
            s3.ObjectLockRetention.governance(duration=Duration.days(365 * 7 + 2))
            if is_prod
            else None
        )

        self.documents_bucket = s3.Bucket(
            self, "DocumentsBucket",
            bucket_name                   = f"codelabs-billing-{env}-documents",
            object_lock_enabled           = True,
            object_lock_default_retention = default_retention,
            block_public_access           = s3.BlockPublicAccess.BLOCK_ALL,
            removal_policy                = RemovalPolicy.RETAIN,
            lifecycle_rules=[
                s3.LifecycleRule(
                    transitions=[
                        s3.Transition(
                            storage_class    = s3.StorageClass.INFREQUENT_ACCESS,
                            transition_after = Duration.days(30),
                        ),
                        s3.Transition(
                            storage_class    = s3.StorageClass.GLACIER_INSTANT_RETRIEVAL,
                            transition_after = Duration.days(90),
                        ),
                    ]
                )
            ],
        )

        CfnOutput(
            self, "DocumentsBucketName",
            value       = self.documents_bucket.bucket_name,
            export_name = f"CodeLabsBilling-{env}-DocumentsBucketName",
        )
        CfnOutput(
            self, "DocumentsBucketArn",
            value       = self.documents_bucket.bucket_arn,
            export_name = f"CodeLabsBilling-{env}-DocumentsBucketArn",
        )
