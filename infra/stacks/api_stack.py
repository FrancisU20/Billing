"""
ApiStack — Lambda functions + HTTP API Gateway + dominio personalizado.

Lambdas:
  tenants           → CRUD empresas (HTTP REST, JWT-protected)
  tenant-onboarding → worker SQS: crea usuario owner en Cognito

API Gateway:
  HTTP API v2 con JWT authorizer nativo apuntando al Cognito User Pool.
  Dominio personalizado vía ACM + Route53 (ej. api-billing-dev.codelabsecuador.com).
  CORS habilitado para el frontend Expo web.

Bundling:
  Local bundler (sin Docker): pip descarga wheels ARM64 con --platform
  manylinux2014_aarch64 y copia el código fuente al asset output.
  Esto coincide con la arquitectura Graviton2 del Lambda sin necesitar Docker.
"""
import shutil
import subprocess
from pathlib import Path

import aws_cdk as cdk
import jsii
from aws_cdk import (
    BundlingOptions,
    CfnOutput,
    Duration,
    ILocalBundling,
    Stack,
    aws_apigatewayv2 as apigwv2,
    aws_apigatewayv2_authorizers as authorizers,
    aws_apigatewayv2_integrations as integrations,
    aws_certificatemanager as acm,
    aws_iam as iam,
    aws_lambda as lmb,
    aws_lambda_event_sources as event_sources,
    aws_route53 as route53,
    aws_route53_targets as targets,
)
from constructs import Construct

# Raíz del código fuente — relativo al CDK app que corre desde infra/
_BACKEND = str(Path(__file__).parent.parent.parent / "backend")


@jsii.implements(ILocalBundling)
class _PythonLocalBundler:
    """
    Instala dependencias ARM64 via pip y copia el código fuente.
    Evita Docker: pip descarga los wheels pre-compilados para
    manylinux2014_aarch64 (Graviton2) directamente desde PyPI.
    """

    def try_bundle(self, output_dir: str, options: BundlingOptions) -> bool:
        try:
            subprocess.run(
                [
                    "pip", "install",
                    "-r", str(Path(_BACKEND) / "requirements.txt"),
                    "-t", output_dir,
                    "--platform", "manylinux2014_aarch64",
                    "--only-binary=:all:",
                    "--implementation", "cp",
                    "--python-version", "3.12",
                    "--quiet",
                ],
                check=True,
            )
            shutil.copytree(
                _BACKEND,
                output_dir,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns(".venv", "__pycache__", "*.pyc"),
            )
            return True
        except Exception:
            return False


class ApiStack(Stack):
    def __init__(
        self,
        scope:        Construct,
        construct_id: str,
        config:       dict,
        database,           # DatabaseStack — tablas DynamoDB
        auth,               # AuthStack — Cognito User Pool + Web Client
        queues,             # QueuesStack — SQS queues
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        env        = config["env"]
        region     = config["region"]
        domain_cfg = config.get("domain", {})
        cors_cfg   = config.get("cors", {})
        api_domain = domain_cfg.get("api", "")
        hz_name    = domain_cfg.get("hosted_zone", "")
        cors_origins = cors_cfg.get("origins", ["*"] if env != "prod" else [])
        cors_headers = cors_cfg.get("headers", ["authorization", "content-type", "x-idempotency-key"])

        _common_env = {
            "ENV":       env,
            "LOG_LEVEL": "DEBUG" if env != "prod" else "INFO",
            "REGION":    region,
        }

        # ── Bundling — instala deps ARM64 y copia código fuente ───────────────
        # El local bundler corre primero (sin Docker). Si falla, CDK intenta
        # Docker como fallback (útil en CI con Docker disponible).
        _code = lmb.Code.from_asset(
            _BACKEND,
            exclude=[".venv", ".venv/**", "**/__pycache__", "**/__pycache__/**", "**/*.pyc"],
            bundling=cdk.BundlingOptions(
                image   = lmb.Runtime.PYTHON_3_12.bundling_image,
                local   = _PythonLocalBundler(),
                command = [
                    "bash", "-c",
                    "pip install -r requirements.txt -t /asset-output"
                    " --platform manylinux2014_aarch64"
                    " --only-binary=:all:"
                    " --implementation cp"
                    " --python-version 3.12"
                    " --quiet"
                    " && cp -au . /asset-output",
                ],
            ),
        )

        # ── Tenants Lambda ─────────────────────────────────────────────────────
        tenants_fn = lmb.Function(
            self, "TenantsFunction",
            function_name = f"codelabs-billing-{env}-tenants",
            runtime       = lmb.Runtime.PYTHON_3_12,
            architecture  = lmb.Architecture.ARM_64,
            code          = _code,
            handler       = "lambdas.tenants.handler.handler",
            timeout       = Duration.seconds(30),
            memory_size   = 256,
            environment   = {
                **_common_env,
                "TENANTS_TABLE":     database.tenants_table.table_name,
                "PLANS_TABLE":       database.plans_table.table_name,
                "AUDIT_LOG_TABLE":   database.audit_table.table_name,
                "IDEMPOTENCY_TABLE": database.idempotency_table.table_name,
                "OUTBOX_TABLE":      database.outbox_table.table_name,
            },
        )
        database.tenants_table.grant_read_write_data(tenants_fn)
        database.plans_table.grant_read_data(tenants_fn)
        database.audit_table.grant_read_write_data(tenants_fn)
        database.idempotency_table.grant_read_write_data(tenants_fn)
        database.outbox_table.grant_write_data(tenants_fn)

        # ── Outbox Relay Worker ───────────────────────────────────────────────
        outbox_relay_fn = lmb.Function(
            self, "OutboxRelayWorker",
            function_name = f"codelabs-billing-{env}-outbox-relay",
            runtime       = lmb.Runtime.PYTHON_3_12,
            architecture  = lmb.Architecture.ARM_64,
            code          = _code,
            handler       = "lambdas.workers.outbox_relay.handler.handler",
            timeout       = Duration.seconds(30),
            memory_size   = 256,
            environment   = {
                **_common_env,
                "OUTBOX_TABLE":     database.outbox_table.table_name,
                "EVENTS_QUEUE_URL": queues.tenant_onboarding_queue.queue_url,
            },
        )
        outbox_relay_fn.add_event_source(
            event_sources.DynamoEventSource(
                database.outbox_table,
                starting_position          = lmb.StartingPosition.TRIM_HORIZON,
                batch_size                 = 10,
                report_batch_item_failures = True,
                bisect_batch_on_error      = True,
            )
        )
        database.outbox_table.grant_stream_read(outbox_relay_fn)
        database.outbox_table.grant_read_write_data(outbox_relay_fn)
        queues.tenant_onboarding_queue.grant_send_messages(outbox_relay_fn)

        # ── Tenant Onboarding Worker ───────────────────────────────────────────
        # timeout = 60s → visibility_timeout SQS = 360s (6×) definido en QueuesStack
        onboarding_fn = lmb.Function(
            self, "TenantOnboardingWorker",
            function_name = f"codelabs-billing-{env}-tenant-onboarding",
            runtime       = lmb.Runtime.PYTHON_3_12,
            architecture  = lmb.Architecture.ARM_64,
            code          = _code,
            handler       = "lambdas.workers.tenant_onboarding.handler.handler",
            timeout       = Duration.seconds(60),
            memory_size   = 256,
            environment   = {
                **_common_env,
                "COGNITO_USER_POOL_ID":          auth.user_pool.user_pool_id,
                "EMAIL_NOTIFICATIONS_QUEUE_URL": queues.email_notifications_queue.queue_url,
            },
        )
        onboarding_fn.add_event_source(
            event_sources.SqsEventSource(
                queues.tenant_onboarding_queue,
                batch_size                 = 5,
                report_batch_item_failures = True,
            )
        )
        onboarding_fn.add_to_role_policy(iam.PolicyStatement(
            actions   = [
                "cognito-idp:AdminCreateUser",
                "cognito-idp:AdminGetUser",
                "cognito-idp:AdminSetUserPassword",
            ],
            resources = [auth.user_pool.user_pool_arn],
        ))
        queues.email_notifications_queue.grant_send_messages(onboarding_fn)
        queues.email_notifications_key.grant_encrypt_decrypt(onboarding_fn)

        # ── Email Notifications Worker ─────────────────────────────────────────
        # timeout = 30s → visibility_timeout SQS = 180s (6×) definido en QueuesStack
        email_notifications_fn = lmb.Function(
            self, "EmailNotificationsWorker",
            function_name = f"codelabs-billing-{env}-email-notifications",
            runtime       = lmb.Runtime.PYTHON_3_12,
            architecture  = lmb.Architecture.ARM_64,
            code          = _code,
            handler       = "lambdas.workers.email_notifications.handler.handler",
            timeout       = Duration.seconds(30),
            memory_size   = 256,
            environment   = {
                **_common_env,
                "BREVO_SECRET_NAME":  f"codelabs-billing-{env}/brevo-api-key",
                "BREVO_SENDER_EMAIL": "noreply@codelabsecuador.com",
                "BREVO_SENDER_NAME":  "CodeLabs Billing",
            },
        )
        email_notifications_fn.add_event_source(
            event_sources.SqsEventSource(
                queues.email_notifications_queue,
                batch_size                 = 5,
                report_batch_item_failures = True,
            )
        )
        queues.email_notifications_key.grant_encrypt_decrypt(email_notifications_fn)
        email_notifications_fn.add_to_role_policy(iam.PolicyStatement(
            actions   = ["secretsmanager:GetSecretValue"],
            resources = [
                f"arn:aws:secretsmanager:{region}:*:secret:codelabs-billing-{env}/brevo-api-key*"
            ],
        ))

        # ── Dominio personalizado — ACM + Route53 ─────────────────────────────
        # El certificado va en la misma región que el API Gateway (sa-east-1).
        # Distinto al certificado del frontend (CloudFront), que debe ir en us-east-1.
        domain_mapping = None
        if api_domain and hz_name:
            hosted_zone = route53.HostedZone.from_lookup(
                self, "HostedZone",
                domain_name = hz_name,
            )

            certificate = acm.Certificate(
                self, "ApiCertificate",
                domain_name = api_domain,
                validation  = acm.CertificateValidation.from_dns(hosted_zone),
            )

            api_domain_name = apigwv2.DomainName(
                self, "ApiDomainName",
                domain_name = api_domain,
                certificate = certificate,
            )

            route53.ARecord(
                self, "ApiDnsRecord",
                zone        = hosted_zone,
                record_name = api_domain,
                target      = route53.RecordTarget.from_alias(
                    targets.ApiGatewayv2DomainProperties(
                        api_domain_name.regional_domain_name,
                        api_domain_name.regional_hosted_zone_id,
                    )
                ),
            )

            domain_mapping = apigwv2.DomainMappingOptions(
                domain_name = api_domain_name,
            )

        # ── HTTP API Gateway ───────────────────────────────────────────────────
        jwt_authorizer = authorizers.HttpJwtAuthorizer(
            "CognitoAuthorizer",
            jwt_issuer   = f"https://cognito-idp.{region}.amazonaws.com/{auth.user_pool.user_pool_id}",
            jwt_audience = [auth.web_client.user_pool_client_id],
        )

        api = apigwv2.HttpApi(
            self, "HttpApi",
            api_name              = f"codelabs-billing-{env}",
            default_domain_mapping= domain_mapping,
            cors_preflight        = apigwv2.CorsPreflightOptions(
                allow_origins = cors_origins,
                allow_methods = [apigwv2.CorsHttpMethod.ANY],
                allow_headers = cors_headers,
            ),
        )

        tenants_integration = integrations.HttpLambdaIntegration(
            "TenantsIntegration", tenants_fn
        )

        for method, route in [
            (apigwv2.HttpMethod.POST,   "/tenants"),
            (apigwv2.HttpMethod.GET,    "/tenants"),
            (apigwv2.HttpMethod.GET,    "/tenants/{id}"),
            (apigwv2.HttpMethod.PATCH,  "/tenants/{id}"),
            (apigwv2.HttpMethod.PATCH,  "/tenants/{id}/status"),
            (apigwv2.HttpMethod.DELETE, "/tenants/{id}"),
        ]:
            api.add_routes(
                path        = route,
                methods     = [method],
                integration = tenants_integration,
                authorizer  = jwt_authorizer,
            )

        # ── Auth Lambda ───────────────────────────────────────────────────────
        auth_fn = lmb.Function(
            self, "AuthFunction",
            function_name = f"codelabs-billing-{env}-auth",
            runtime       = lmb.Runtime.PYTHON_3_12,
            architecture  = lmb.Architecture.ARM_64,
            code          = _code,
            handler       = "lambdas.auth.handler.handler",
            timeout       = Duration.seconds(15),
            memory_size   = 256,
            environment   = {
                **_common_env,
                "COGNITO_USER_POOL_ID": auth.user_pool.user_pool_id,
                "COGNITO_WEB_CLIENT_ID": auth.web_client.user_pool_client_id,
            },
        )
        auth_fn.add_to_role_policy(iam.PolicyStatement(
            actions   = [
                "cognito-idp:InitiateAuth",
                "cognito-idp:RespondToAuthChallenge",
                "cognito-idp:GlobalSignOut",
            ],
            resources = [auth.user_pool.user_pool_arn],
        ))

        auth_integration = integrations.HttpLambdaIntegration(
            "AuthIntegration", auth_fn
        )

        # Public by design: these routes issue or complete Cognito tokens.
        for route in [
            "/auth/login",
            "/auth/refresh",
            "/auth/logout",
            "/auth/challenge",
        ]:
            api.add_routes(
                path        = route,
                methods     = [apigwv2.HttpMethod.POST],
                integration = auth_integration,
            )

        # ── Plans Lambda ───────────────────────────────────────────────────────
        plans_fn = lmb.Function(
            self, "PlansFunction",
            function_name = f"codelabs-billing-{env}-plans",
            runtime       = lmb.Runtime.PYTHON_3_12,
            architecture  = lmb.Architecture.ARM_64,
            code          = _code,
            handler       = "lambdas.plans.handler.handler",
            timeout       = Duration.seconds(15),
            memory_size   = 256,
            environment   = {
                **_common_env,
                "PLANS_TABLE":       database.plans_table.table_name,
                "AUDIT_LOG_TABLE":   database.audit_table.table_name,
                "IDEMPOTENCY_TABLE": database.idempotency_table.table_name,
            },
        )
        database.plans_table.grant_read_write_data(plans_fn)
        database.audit_table.grant_read_write_data(plans_fn)
        database.idempotency_table.grant_read_write_data(plans_fn)

        plans_integration = integrations.HttpLambdaIntegration(
            "PlansIntegration", plans_fn
        )

        # GET /plans y GET /plans/{id} son públicos (sin auth) para mostrar pricing
        for method, route in [
            (apigwv2.HttpMethod.GET, "/plans"),
            (apigwv2.HttpMethod.GET, "/plans/{id}"),
        ]:
            api.add_routes(
                path        = route,
                methods     = [method],
                integration = plans_integration,
            )

        # POST / PATCH requieren superadmin
        for method, route in [
            (apigwv2.HttpMethod.POST,  "/plans"),
            (apigwv2.HttpMethod.PATCH, "/plans/{id}"),
            (apigwv2.HttpMethod.PATCH, "/plans/{id}/status"),
        ]:
            api.add_routes(
                path        = route,
                methods     = [method],
                integration = plans_integration,
                authorizer  = jwt_authorizer,
            )

        # ── Outputs ───────────────────────────────────────────────────────────
        CfnOutput(self, "ApiUrl",
                  value       = api.url or "",
                  export_name = f"CodeLabsBilling-{env}-ApiUrl")

        if api_domain:
            CfnOutput(self, "ApiCustomDomain",
                      value       = f"https://{api_domain}",
                      export_name = f"CodeLabsBilling-{env}-ApiCustomDomain")
