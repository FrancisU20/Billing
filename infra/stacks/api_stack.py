from aws_cdk import (
    Stack, Duration,
    aws_ec2 as ec2,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    aws_iam as iam,
    aws_logs as logs,
)
from constructs import Construct
from .database_stack import DatabaseStack
from .storage_stack import StorageStack
from .queues_stack import QueuesStack
from .auth_stack import AuthStack


class ApiStack(Stack):
    def __init__(
        self, scope: Construct, construct_id: str,
        config: dict,
        vpc: ec2.Vpc,
        database: DatabaseStack,
        storage: StorageStack,
        queues: QueuesStack,
        auth: AuthStack,
        **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        env = config["env"]
        lambda_cfg = config["lambda"]

        # Security group para Lambdas en VPC
        self.lambda_sg = ec2.SecurityGroup(
            self, "LambdaSg",
            vpc=vpc,
            security_group_name=f"codelabs-billing-{env}-lambda-sg",
            description="Lambda functions",
            allow_all_outbound=True,  # necesario para llamadas al SRI y providers de email
        )

        # Permitir Lambda → Aurora (o Proxy)
        database.aurora_sg.add_ingress_rule(
            peer=self.lambda_sg,
            connection=ec2.Port.tcp(5432),
            description="Lambda → Aurora",
        )

        # Rol base compartido para Lambdas
        base_role = iam.Role(
            self, "LambdaBaseRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
            ],
        )

        # Grants: Secrets Manager, S3, SQS
        database.connection_secret.grant_read(base_role)
        storage.documents_bucket.grant_read_write(base_role)
        storage.assets_bucket.grant_read_write(base_role)
        storage.batches_bucket.grant_read_write(base_role)
        queues.invoice_processing_queue.grant_send_messages(base_role)
        queues.sri_authorization_queue.grant_send_messages(base_role)
        queues.email_dispatch_queue.grant_send_messages(base_role)
        queues.batch_import_queue.grant_send_messages(base_role)

        vpc_config = {
            "vpc": vpc,
            "vpc_subnets": ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS),
            "security_groups": [self.lambda_sg],
        }

        common_env = {
            "ENV": env,
            "AWS_ACCOUNT_ID": self.account,
            "AWS_REGION_NAME": self.region,
            "DB_SECRET_ARN": database.connection_secret.secret_arn,
            "DB_HOST": database.connection_host,
            "DB_NAME": config["aurora"]["database_name"],
            "S3_DOCUMENTS_BUCKET": storage.documents_bucket.bucket_name,
            "S3_ASSETS_BUCKET": storage.assets_bucket.bucket_name,
            "S3_BATCHES_BUCKET": storage.batches_bucket.bucket_name,
            "SQS_INVOICE_PROCESSING_URL": queues.invoice_processing_queue.queue_url,
            "SQS_SRI_AUTHORIZATION_URL": queues.sri_authorization_queue.queue_url,
            "SQS_EMAIL_DISPATCH_URL": queues.email_dispatch_queue.queue_url,
            "SQS_BATCH_IMPORT_URL": queues.batch_import_queue.queue_url,
            "COGNITO_USER_POOL_ID": auth.user_pool.user_pool_id,
            "COGNITO_WEB_CLIENT_ID": auth.web_client.user_pool_client_id,
            "POWERTOOLS_SERVICE_NAME": "codelabs-billing",
            "POWERTOOLS_LOG_LEVEL": lambda_cfg["powertools_log_level"],
        }

        lambda_props = dict(
            runtime=_lambda.Runtime.PYTHON_3_12,
            memory_size=lambda_cfg["memory_mb"],
            timeout=Duration.seconds(lambda_cfg["timeout_seconds"]),
            role=base_role,
            environment=common_env,
            log_retention=logs.RetentionDays.ONE_WEEK if env != "prod" else logs.RetentionDays.THREE_MONTHS,
            tracing=_lambda.Tracing.ACTIVE,
            **vpc_config,
        )

        # Lambda API (FastAPI + Mangum)
        self.api_function = _lambda.Function(
            self, "ApiFunction",
            function_name=f"codelabs-billing-{env}-api",
            code=_lambda.Code.from_asset("../backend"),
            handler="lambda_handlers.api_handler.handler",
            **lambda_props,
        )

        # Lambda workers — uno por cola
        self.invoice_worker = _lambda.Function(
            self, "InvoiceWorker",
            function_name=f"codelabs-billing-{env}-invoice-worker",
            code=_lambda.Code.from_asset("../backend"),
            handler="lambda_handlers.invoice_worker_handler.handler",
            memory_size=512,  # PDF generation necesita más memoria
            timeout=Duration.seconds(300),
            role=base_role,
            environment=common_env,
            log_retention=logs.RetentionDays.ONE_WEEK if env != "prod" else logs.RetentionDays.THREE_MONTHS,
            tracing=_lambda.Tracing.ACTIVE,
            **vpc_config,
        )
        queues.invoice_processing_queue.grant_consume_messages(self.invoice_worker)

        self.sri_retry_worker = _lambda.Function(
            self, "SriRetryWorker",
            function_name=f"codelabs-billing-{env}-sri-retry-worker",
            code=_lambda.Code.from_asset("../backend"),
            handler="lambda_handlers.sri_retry_handler.handler",
            **lambda_props,
        )
        queues.sri_authorization_queue.grant_consume_messages(self.sri_retry_worker)

        self.email_dispatch_worker = _lambda.Function(
            self, "EmailDispatchWorker",
            function_name=f"codelabs-billing-{env}-email-dispatch-worker",
            code=_lambda.Code.from_asset("../backend"),
            handler="lambda_handlers.email_dispatch_handler.handler",
            **lambda_props,
        )
        queues.email_dispatch_queue.grant_consume_messages(self.email_dispatch_worker)

        self.batch_import_worker = _lambda.Function(
            self, "BatchImportWorker",
            function_name=f"codelabs-billing-{env}-batch-import-worker",
            code=_lambda.Code.from_asset("../backend"),
            handler="lambda_handlers.batch_import_handler.handler",
            memory_size=512,
            timeout=Duration.seconds(600),
            role=base_role,
            environment=common_env,
            log_retention=logs.RetentionDays.ONE_WEEK if env != "prod" else logs.RetentionDays.THREE_MONTHS,
            tracing=_lambda.Tracing.ACTIVE,
            **vpc_config,
        )
        queues.batch_import_queue.grant_consume_messages(self.batch_import_worker)

        # SQS event source mappings
        from aws_cdk import aws_lambda_event_sources as event_sources
        self.invoice_worker.add_event_source(
            event_sources.SqsEventSource(queues.invoice_processing_queue, batch_size=1)
        )
        self.sri_retry_worker.add_event_source(
            event_sources.SqsEventSource(queues.sri_authorization_queue, batch_size=5)
        )
        self.email_dispatch_worker.add_event_source(
            event_sources.SqsEventSource(queues.email_dispatch_queue, batch_size=10)
        )
        self.batch_import_worker.add_event_source(
            event_sources.SqsEventSource(queues.batch_import_queue, batch_size=1)
        )

        # API Gateway REST
        log_group = logs.LogGroup(
            self, "ApiGatewayLogs",
            log_group_name=f"/aws/apigateway/codelabs-billing-{env}",
            retention=logs.RetentionDays.ONE_WEEK if env != "prod" else logs.RetentionDays.THREE_MONTHS,
        )

        self.api = apigw.RestApi(
            self, "RestApi",
            rest_api_name=f"codelabs-billing-{env}",
            description="CodeLabs Billing Cloud API",
            deploy_options=apigw.StageOptions(
                stage_name=env,
                logging_level=apigw.MethodLoggingLevel.INFO,
                data_trace_enabled=False,  # nunca loguear request/response bodies (datos sensibles)
                metrics_enabled=True,
                access_log_destination=apigw.LogGroupLogDestination(log_group),
                throttling_rate_limit=1000,
                throttling_burst_limit=500,
                tracing_enabled=True,
            ),
            default_cors_preflight_options=apigw.CorsOptions(
                allow_origins=apigw.Cors.ALL_ORIGINS if env == "dev" else ["https://app.codelasbilling.com"],
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "Authorization", "X-Api-Key", "X-Idempotency-Key"],
            ),
        )

        # Proxy completo a Lambda API
        api_integration = apigw.LambdaIntegration(self.api_function)
        proxy = self.api.root.add_resource("{proxy+}")
        proxy.add_method("ANY", api_integration)
        self.api.root.add_method("ANY", api_integration)
