from aws_cdk import (
    Stack, RemovalPolicy, Duration,
    aws_s3 as s3,
    aws_kms as kms,
)
from constructs import Construct


class StorageStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, config: dict, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        env = config["env"]
        s3_cfg = config["s3"]

        # KMS key para S3
        self.s3_key = kms.Key(
            self, "S3Key",
            alias=f"codelabs-billing-{env}-s3",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.RETAIN if env == "prod" else RemovalPolicy.DESTROY,
        )

        lifecycle_rules = [
            s3.LifecycleRule(
                id="TransitionToIA",
                enabled=True,
                transitions=[
                    s3.Transition(
                        storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                        transition_after=Duration.days(s3_cfg["lifecycle_transition_ia_days"]),
                    ),
                    s3.Transition(
                        storage_class=s3.StorageClass.GLACIER_INSTANT_RETRIEVAL,
                        transition_after=Duration.days(s3_cfg["lifecycle_transition_glacier_days"]),
                    ),
                ],
                expiration=Duration.days(s3_cfg["lifecycle_expiration_days"]),
            )
        ]

        removal = RemovalPolicy.RETAIN if env == "prod" else RemovalPolicy.DESTROY
        auto_delete = env != "prod"

        # Bucket principal: XML firmados, XML autorizados, PDF/RIDE, certificados
        self.documents_bucket = s3.Bucket(
            self, "DocumentsBucket",
            bucket_name=f"codelabs-billing-{env}-documents",
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.s3_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=True,
            lifecycle_rules=lifecycle_rules,
            removal_policy=removal,
            auto_delete_objects=auto_delete,
            enforce_ssl=True,
        )

        # Bucket assets: logos, plantillas de tenants
        self.assets_bucket = s3.Bucket(
            self, "AssetsBucket",
            bucket_name=f"codelabs-billing-{env}-assets",
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.s3_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=False,
            removal_policy=removal,
            auto_delete_objects=auto_delete,
            enforce_ssl=True,
        )

        # Bucket batches: archivos CSV/Excel de carga masiva y resultados
        self.batches_bucket = s3.Bucket(
            self, "BatchesBucket",
            bucket_name=f"codelabs-billing-{env}-batches",
            encryption=s3.BucketEncryption.KMS,
            encryption_key=self.s3_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            versioned=False,
            lifecycle_rules=[
                # Archivos de batch se eliminan a los 90 días (solo los resultados van a documents)
                s3.LifecycleRule(
                    id="BatchExpiry",
                    enabled=True,
                    expiration=Duration.days(90),
                )
            ],
            removal_policy=removal,
            auto_delete_objects=auto_delete,
            enforce_ssl=True,
        )
