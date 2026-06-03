from aws_cdk import (
    Stack, Duration, CfnOutput,
    aws_ec2 as ec2,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    aws_iam as iam,
    aws_logs as logs,
    aws_route53 as route53,
    aws_route53_targets as targets,
)
from aws_cdk.aws_certificatemanager import ICertificate
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
        api_cert: ICertificate | None = None,
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

        # Permitir Lambda → Aurora usando el CIDR de la VPC
        # (evita ciclo de dependencia SG cross-stack)
        database.aurora_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(5432),
            description="Lambda to Aurora via VPC CIDR",
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

        # Grants: Secrets Manager — inline policy en lugar de grant_read()
        # grant_read() modifica la resource policy del Secret (en DatabaseStack),
        # creando una dependencia cruzada Database→Api que causa ciclo.
        # Inline policy en el rol evita el ciclo.
        base_role.add_to_policy(iam.PolicyStatement(
            actions=["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"],
            resources=[database.connection_secret.secret_arn],
        ))
        base_role.add_to_policy(iam.PolicyStatement(
            actions=["kms:Decrypt", "kms:DescribeKey"],
            resources=[database.db_key.key_arn],
            conditions={
                "StringEquals": {
                    "kms:ViaService": f"secretsmanager.{self.region}.amazonaws.com",
                },
            },
        ))
        # SSM Parameter Store: configuración no-sensible (ej. tarifa IVA vigente)
        base_role.add_to_policy(iam.PolicyStatement(
            actions=["ssm:GetParameter", "ssm:GetParameters"],
            resources=[f"arn:aws:ssm:{self.region}:{self.account}:parameter/codelabs-billing/{env}/*"],
        ))
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

        # Dos Lambda Layers separados para mantener tamaños bajo los 250MB:
        #   core-layer (~130MB): FastAPI, SQLAlchemy, zeep, lxml, cryptography, etc.
        #   batch-layer (~69MB): pandas, openpyxl — solo para batch_import_worker
        # Construidos en CI (GitHub Actions = Linux) — correcto SO para los wheels nativos
        core_layer = _lambda.LayerVersion(
            self, "CoreLayer",
            layer_version_name=f"codelabs-billing-{env}-core",
            code=_lambda.Code.from_asset("./lambda_layer/core"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_12],
            description=f"Core Python dependencies — {env}",
        )

        batch_layer = _lambda.LayerVersion(
            self, "BatchLayer",
            layer_version_name=f"codelabs-billing-{env}-batch",
            code=_lambda.Code.from_asset("./lambda_layer/batch"),
            compatible_runtimes=[_lambda.Runtime.PYTHON_3_12],
            description=f"Batch processing Python dependencies (pandas/numpy) — {env}",
        )

        # Solo código de la aplicación en el zip (<10MB sin dependencias)
        _APP_CODE_EXCLUDES = [
            ".venv", "__pycache__", "*.pyc", "*.pyo",
            ".pytest_cache", "htmlcov", ".coverage",
            "tests/", "*.egg-info", "dist/", "build/",
        ]

        def backend_code() -> _lambda.AssetCode:
            return _lambda.Code.from_asset(
                "../backend",
                exclude=_APP_CODE_EXCLUDES,
            )

        lambda_props = dict(
            layers=[core_layer],
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
            code=backend_code(),
            handler="lambda_handlers.api_handler.handler",
            **lambda_props,
        )

        # Lambda workers — uno por cola
        self.invoice_worker = _lambda.Function(
            self, "InvoiceWorker",
            function_name=f"codelabs-billing-{env}-invoice-worker",
            code=backend_code(),
            handler="lambda_handlers.invoice_worker_handler.handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
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
            code=backend_code(),
            handler="lambda_handlers.sri_retry_handler.handler",
            **lambda_props,
        )
        queues.sri_authorization_queue.grant_consume_messages(self.sri_retry_worker)

        self.email_dispatch_worker = _lambda.Function(
            self, "EmailDispatchWorker",
            function_name=f"codelabs-billing-{env}-email-dispatch-worker",
            code=backend_code(),
            handler="lambda_handlers.email_dispatch_handler.handler",
            **lambda_props,
        )
        queues.email_dispatch_queue.grant_consume_messages(self.email_dispatch_worker)

        self.batch_import_worker = _lambda.Function(
            self, "BatchImportWorker",
            function_name=f"codelabs-billing-{env}-batch-import-worker",
            code=backend_code(),
            handler="lambda_handlers.batch_import_handler.handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            memory_size=512,
            timeout=Duration.seconds(600),
            role=base_role,
            environment=common_env,
            # Batch worker necesita ambos layers: core + batch (pandas/numpy)
            layers=[core_layer, batch_layer],
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
                allow_origins=(
                    apigw.Cors.ALL_ORIGINS if env == "dev"
                    else [f"https://{config['domain']['frontend']}"]
                ),
                allow_methods=apigw.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "Authorization", "X-Api-Key", "X-Idempotency-Key"],
            ),
        )

        cors_error_origin = (
            "'*'" if env == "dev"
            else f"'https://{config['domain']['frontend']}'"
        )
        cors_error_headers = {
            "Access-Control-Allow-Origin": cors_error_origin,
            "Access-Control-Allow-Headers": "'Content-Type,Authorization,X-Api-Key,X-Idempotency-Key'",
            "Access-Control-Allow-Methods": "'OPTIONS,GET,POST,PUT,PATCH,DELETE,HEAD'",
        }
        self.api.add_gateway_response(
            "Default4xxCorsResponse",
            type=apigw.ResponseType.DEFAULT_4_XX,
            response_headers=cors_error_headers,
        )
        self.api.add_gateway_response(
            "Default5xxCorsResponse",
            type=apigw.ResponseType.DEFAULT_5_XX,
            response_headers=cors_error_headers,
        )

        # Lambda Authorizer — valida JWT Cognito, extrae tenant_id + rol
        # Necesita python-jose para verificar RS256; se incluye en requirements.txt
        authorizer_fn = _lambda.Function(
            self, "AuthorizerFunction",
            function_name=f"codelabs-billing-{env}-authorizer",
            code=backend_code(),
            handler="lambda_handlers.authorizer_handler.handler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            memory_size=256,
            timeout=Duration.seconds(10),
            layers=[core_layer],
            environment={
                "AWS_REGION_NAME": self.region,
                "COGNITO_USER_POOL_ID": auth.user_pool.user_pool_id,
                "COGNITO_WEB_CLIENT_ID": auth.web_client.user_pool_client_id,
                "POWERTOOLS_LOG_LEVEL": lambda_cfg["powertools_log_level"],
            },
            log_retention=logs.RetentionDays.ONE_WEEK,
        )

        authorizer = apigw.TokenAuthorizer(
            self, "CognitoAuthorizer",
            authorizer_name=f"codelabs-billing-{env}-authorizer",
            handler=authorizer_fn,
            results_cache_ttl=Duration.minutes(5),  # cachea el resultado 5 min — reduce invocaciones
            identity_source="method.request.header.Authorization",
        )

        # Proxy completo a Lambda API con authorizer
        api_integration = apigw.LambdaIntegration(self.api_function)
        proxy = self.api.root.add_resource("{proxy+}")
        proxy.add_method("ANY", api_integration, authorizer=authorizer)
        self.api.root.add_method("ANY", api_integration, authorizer=authorizer)

        # Custom domain para API Gateway (api-billing-dev.codelabsecuador.com)
        # Requiere certificado wildcard en sa-east-1 (inyectado desde SecurityStack)
        domain_cfg = config["domain"]
        if api_cert is not None:
            custom_domain = apigw.DomainName(
                self, "ApiCustomDomain",
                domain_name=domain_cfg["api"],
                certificate=api_cert,
                endpoint_type=apigw.EndpointType.REGIONAL,
                security_policy=apigw.SecurityPolicy.TLS_1_2,
            )

            apigw.BasePathMapping(
                self, "ApiBasePathMapping",
                domain_name=custom_domain,
                rest_api=self.api,
                stage=self.api.deployment_stage,
            )

            # Route 53 — alias record para el custom domain de API Gateway
            hosted_zone = route53.HostedZone.from_hosted_zone_attributes(
                self, "HostedZone",
                hosted_zone_id=domain_cfg["hosted_zone_id"],
                zone_name=domain_cfg["hosted_zone"],
            )

            route53.ARecord(
                self, "ApiAliasRecord",
                zone=hosted_zone,
                record_name=domain_cfg["api"],
                target=route53.RecordTarget.from_alias(
                    targets.ApiGatewayDomain(custom_domain)
                ),
            )

            CfnOutput(self, "ApiCustomDomainUrl",
                      value=f"https://{domain_cfg['api']}",
                      export_name=f"CodeLabsBilling-{env}-ApiCustomDomainUrl")

        # Outputs para CI/CD — leídos dinámicamente en GitHub Actions
        CfnOutput(self, "ApiGatewayEndpoint",
                  value=self.api.url,
                  export_name=f"CodeLabsBilling-{env}-ApiGatewayEndpoint")
