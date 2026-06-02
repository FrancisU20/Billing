from aws_cdk import (
    Stack, RemovalPolicy, Duration,
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_kms as kms,
    aws_secretsmanager as secretsmanager,
)
from constructs import Construct


class DatabaseStack(Stack):
    def __init__(
        self, scope: Construct, construct_id: str,
        config: dict, vpc: ec2.Vpc, **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        env = config["env"]
        aurora_cfg = config["aurora"]

        # KMS key dedicada para Aurora
        self.db_key = kms.Key(
            self, "AuroraKey",
            alias=f"codelabs-billing-{env}-aurora",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.RETAIN if env == "prod" else RemovalPolicy.DESTROY,
        )

        # Security group para Aurora — solo acceso desde Lambda SG (se añade en ApiStack)
        self.aurora_sg = ec2.SecurityGroup(
            self, "AuroraSg",
            vpc=vpc,
            security_group_name=f"codelabs-billing-{env}-aurora-sg",
            description="Aurora PostgreSQL access",
            allow_all_outbound=False,
        )

        # Cluster Aurora Serverless v2
        self.cluster = rds.DatabaseCluster(
            self, "AuroraCluster",
            cluster_identifier=f"codelabs-billing-{env}",
            engine=rds.DatabaseClusterEngine.aurora_postgres(
                version=rds.AuroraPostgresEngineVersion.VER_16_2,
            ),
            serverless_v2_min_capacity=aurora_cfg["min_capacity"],
            serverless_v2_max_capacity=aurora_cfg["max_capacity"],
            writer=rds.ClusterInstance.serverless_v2("Writer"),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            security_groups=[self.aurora_sg],
            default_database_name=aurora_cfg["database_name"],
            storage_encrypted=True,
            storage_encryption_key=self.db_key,
            backup=rds.BackupProps(
                retention=Duration.days(7 if env != "prod" else 30),
            ),
            deletion_protection=env == "prod",
            removal_policy=RemovalPolicy.RETAIN if env == "prod" else RemovalPolicy.DESTROY,
            enable_data_api=False,  # SQLAlchemy usa conexión directa
            credentials=rds.Credentials.from_generated_secret(
                username="clbilling_admin",
                secret_name=f"codelabs-billing/{env}/db/master",
                encryption_key=self.db_key,
            ),
        )

        # RDS Proxy — solo si está habilitado en config (producción)
        self.proxy = None
        if config["rds_proxy"]["enabled"]:
            self.proxy_sg = ec2.SecurityGroup(
                self, "ProxySg",
                vpc=vpc,
                security_group_name=f"codelabs-billing-{env}-proxy-sg",
                description="RDS Proxy access",
                allow_all_outbound=False,
            )
            # Proxy SG puede hablar con Aurora SG
            self.aurora_sg.add_ingress_rule(
                peer=self.proxy_sg,
                connection=ec2.Port.tcp(5432),
                description="RDS Proxy → Aurora",
            )
            self.proxy = rds.DatabaseProxy(
                self, "AuroraProxy",
                proxy_target=rds.ProxyTarget.from_cluster(self.cluster),
                secrets=[self.cluster.secret],
                vpc=vpc,
                vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
                security_groups=[self.proxy_sg],
                require_tls=True,
                db_proxy_name=f"codelabs-billing-{env}-proxy",
            )

    @property
    def connection_secret(self):
        return self.cluster.secret

    @property
    def connection_host(self):
        if self.proxy:
            return self.proxy.endpoint
        return self.cluster.cluster_endpoint.hostname
