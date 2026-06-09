"""
DatabaseStack — tablas DynamoDB del sistema.

Una tabla por dominio funcional. Cada tabla tiene sus propios GSIs
definidos según los access patterns de ese dominio.

Convención de nombres: codelabs-billing-{env}-{tabla}

Stacks separados por responsabilidad:
- DatabaseStack: solo DynamoDB (este archivo)
- ApiStack: Lambdas + API Gateway (cuando llegue)
- AuthStack: Cognito (cuando llegue)
- StorageStack: S3 (cuando llegue)
"""
from aws_cdk import (
    Stack, RemovalPolicy, CfnOutput,
    aws_dynamodb as ddb,
)
from constructs import Construct


class DatabaseStack(Stack):
    def __init__(
        self,
        scope:        Construct,
        construct_id: str,
        config:       dict,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        env     = config["env"]
        db_cfg  = config["dynamodb"]
        removal = RemovalPolicy.DESTROY if env != "prod" else RemovalPolicy.RETAIN
        pitr    = db_cfg.get("point_in_time_recovery", False)

        # ── Tenants ────────────────────────────────────────────────────────────
        # PK: id (UUID)
        # GSI ruc-index: PK=ruc → lookup por RUC
        # Unicidad RUC: lock transaccional id="RUC#{ruc}" en esta misma tabla
        self.tenants_table = ddb.Table(
            self, "TenantsTable",
            table_name      = f"codelabs-billing-{env}-tenants",
            partition_key   = ddb.Attribute(name="id", type=ddb.AttributeType.STRING),
            billing_mode    = ddb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery_specification=ddb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=pitr,
            ),
            removal_policy  = removal,
        )
        self.tenants_table.add_global_secondary_index(
            index_name    = "ruc-index",
            partition_key = ddb.Attribute(name="ruc", type=ddb.AttributeType.STRING),
            projection_type = ddb.ProjectionType.ALL,
        )

        # ── Audit Log ──────────────────────────────────────────────────────────
        # PK: "AUDIT#{entity_type}" | SK: "{timestamp}#{action}#{entity_id}"
        # Permite listar auditoría por tipo de entidad ordenada por tiempo
        # TTL = 7 años (retención legal SRI Ecuador); campo "ttl" escrito por shared/audit/writer.py
        self.audit_table = ddb.Table(
            self, "AuditTable",
            table_name             = f"codelabs-billing-{env}-audit",
            partition_key          = ddb.Attribute(name="pk", type=ddb.AttributeType.STRING),
            sort_key               = ddb.Attribute(name="sk", type=ddb.AttributeType.STRING),
            billing_mode           = ddb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute = "ttl",
            point_in_time_recovery_specification=ddb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=pitr,
            ),
            removal_policy = removal,
        )

        # ── Idempotency ────────────────────────────────────────────────────────
        # PK: "{tenant_id}#{idempotency_key}"
        # TTL automático a 24h — DynamoDB borra entradas viejas sin costo adicional
        self.idempotency_table = ddb.Table(
            self, "IdempotencyTable",
            table_name    = f"codelabs-billing-{env}-idempotency",
            partition_key = ddb.Attribute(name="pk", type=ddb.AttributeType.STRING),
            billing_mode  = ddb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute = "ttl",
            point_in_time_recovery_specification=ddb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=pitr,
            ),
            removal_policy = removal,
        )

        # ── Outbox ─────────────────────────────────────────────────────────────
        # PK: id (event_id). Stream NEW_IMAGE dispara relay → SQS.
        self.outbox_table = ddb.Table(
            self, "OutboxTable",
            table_name    = f"codelabs-billing-{env}-outbox",
            partition_key = ddb.Attribute(name="id", type=ddb.AttributeType.STRING),
            billing_mode  = ddb.BillingMode.PAY_PER_REQUEST,
            stream        = ddb.StreamViewType.NEW_IMAGE,
            time_to_live_attribute = "ttl",
            point_in_time_recovery_specification=ddb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=pitr,
            ),
            removal_policy = removal,
        )

        # ── Plans ──────────────────────────────────────────────────────────────
        # PK: id (UUID) — FK estable en Tenant.plan_id
        # GSI slug-index: PK=slug → lookup por slug para rutas públicas
        self.plans_table = ddb.Table(
            self, "PlansTable",
            table_name    = f"codelabs-billing-{env}-plans",
            partition_key = ddb.Attribute(name="id", type=ddb.AttributeType.STRING),
            billing_mode  = ddb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery_specification=ddb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=pitr,
            ),
            removal_policy = removal,
        )
        self.plans_table.add_global_secondary_index(
            index_name      = "slug-index",
            partition_key   = ddb.Attribute(name="slug", type=ddb.AttributeType.STRING),
            projection_type = ddb.ProjectionType.ALL,
        )

        # ── Clients ───────────────────────────────────────────────────────────
        # PK: pk="TENANT#{tenant_id}" | SK: sk="CLIENT#{uuid}"
        # GSI identification-index: PK=tenant_id, SK=identification
        # Unicidad por tenant: lock transaccional SK="CLIENT_IDENTIFICATION#{identification}"
        self.clients_table = ddb.Table(
            self, "ClientsTable",
            table_name      = f"codelabs-billing-{env}-clients",
            partition_key   = ddb.Attribute(name="pk", type=ddb.AttributeType.STRING),
            sort_key        = ddb.Attribute(name="sk", type=ddb.AttributeType.STRING),
            billing_mode    = ddb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery_specification=ddb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=pitr,
            ),
            removal_policy  = removal,
        )
        self.clients_table.add_global_secondary_index(
            index_name      = "identification-index",
            partition_key   = ddb.Attribute(name="tenant_id", type=ddb.AttributeType.STRING),
            sort_key        = ddb.Attribute(name="identification", type=ddb.AttributeType.STRING),
            projection_type = ddb.ProjectionType.ALL,
        )

        # ── Migrations ─────────────────────────────────────────────────────────
        # PK: id (nombre del script, ej. "0001_create_tables")
        # Trackea qué migraciones de datos corrieron
        self.migrations_table = ddb.Table(
            self, "MigrationsTable",
            table_name    = f"codelabs-billing-{env}-migrations",
            partition_key = ddb.Attribute(name="id", type=ddb.AttributeType.STRING),
            billing_mode  = ddb.BillingMode.PAY_PER_REQUEST,
            point_in_time_recovery_specification=ddb.PointInTimeRecoverySpecification(
                point_in_time_recovery_enabled=pitr,
            ),
            removal_policy = removal,
        )

        # ── Outputs para scripts operativos y CI/CD ──────────────────────────
        CfnOutput(self, "TenantsTableName",
                  value=self.tenants_table.table_name,
                  export_name=f"CodeLabsBilling-{env}-TenantsTableName")

        CfnOutput(self, "AuditTableName",
                  value=self.audit_table.table_name,
                  export_name=f"CodeLabsBilling-{env}-AuditTableName")

        CfnOutput(self, "IdempotencyTableName",
                  value=self.idempotency_table.table_name,
                  export_name=f"CodeLabsBilling-{env}-IdempotencyTableName")

        CfnOutput(self, "OutboxTableName",
                  value=self.outbox_table.table_name,
                  export_name=f"CodeLabsBilling-{env}-OutboxTableName")

        CfnOutput(self, "PlansTableName",
                  value=self.plans_table.table_name,
                  export_name=f"CodeLabsBilling-{env}-PlansTableName")

        CfnOutput(self, "ClientsTableName",
                  value=self.clients_table.table_name,
                  export_name=f"CodeLabsBilling-{env}-ClientsTableName")

        CfnOutput(self, "MigrationsTableName",
                  value=self.migrations_table.table_name,
                  export_name=f"CodeLabsBilling-{env}-MigrationsTableName")
