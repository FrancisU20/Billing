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
    aws_events as events,
    aws_events_targets as events_targets,
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
    @staticmethod
    def _grant_certificate_secrets(
        fn: lmb.Function, *, env: str, region: str, allow_delete: bool = False
    ) -> None:
        """Allow a Lambda to manage tenant certificate secrets in Secrets Manager.

        Used by both `certificates` (post-onboarding certificate replacement) and
        `onboarding` (initial certificate upload + orphan cleanup) — same secret
        naming convention. `allow_delete` is only needed by `onboarding`, which
        cleans up orphaned secrets when a transactional commit fails.
        """
        actions = [
            "secretsmanager:CreateSecret",
            "secretsmanager:DescribeSecret",
            "secretsmanager:PutSecretValue",
        ]
        if allow_delete:
            actions.append("secretsmanager:DeleteSecret")

        fn.add_to_role_policy(iam.PolicyStatement(
            actions   = actions,
            resources = [
                f"arn:aws:secretsmanager:{region}:*:secret:/codelabs-billing/{env}/tenant/*"
            ],
        ))

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
        domain_cfg      = config.get("domain", {})
        cors_cfg        = config.get("cors", {})
        api_cfg         = config.get("api", {})
        api_domain      = domain_cfg.get("api", "")
        hz_name         = domain_cfg.get("hosted_zone", "")
        frontend_domain = domain_cfg.get("frontend", "")
        frontend_url    = f"https://{frontend_domain}" if frontend_domain else ""
        cors_origins = cors_cfg.get("origins", ["*"] if env != "prod" else [])
        cors_headers = cors_cfg.get("headers", ["authorization", "content-type", "x-idempotency-key"])
        throttling_cfg = api_cfg.get("throttling", {})

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
                "PAYMENTS_TABLE":    database.payments_table.table_name,
                "AUDIT_LOG_TABLE":   database.audit_table.table_name,
                "IDEMPOTENCY_TABLE": database.idempotency_table.table_name,
                "OUTBOX_TABLE":      database.outbox_table.table_name,
            },
        )
        database.tenants_table.grant_read_write_data(tenants_fn)
        database.plans_table.grant_read_data(tenants_fn)
        database.payments_table.grant_read_write_data(tenants_fn)
        database.audit_table.grant_read_write_data(tenants_fn)
        database.idempotency_table.grant_read_write_data(tenants_fn)
        database.outbox_table.grant_write_data(tenants_fn)

        # ── Certificates Lambda ────────────────────────────────────────────────
        certificates_fn = lmb.Function(
            self, "CertificatesFunction",
            function_name = f"codelabs-billing-{env}-certificates",
            runtime       = lmb.Runtime.PYTHON_3_12,
            architecture  = lmb.Architecture.ARM_64,
            code          = _code,
            handler       = "lambdas.certificates.handler.handler",
            timeout       = Duration.seconds(30),
            memory_size   = 256,
            environment   = {
                **_common_env,
                "TENANTS_TABLE":              database.tenants_table.table_name,
                "AUDIT_LOG_TABLE":            database.audit_table.table_name,
                "IDEMPOTENCY_TABLE":          database.idempotency_table.table_name,
                "CERTIFICATE_SECRET_PREFIX":  f"/codelabs-billing/{env}/tenant",
            },
        )
        database.tenants_table.grant_read_write_data(certificates_fn)
        database.audit_table.grant_read_write_data(certificates_fn)
        database.idempotency_table.grant_read_write_data(certificates_fn)
        self._grant_certificate_secrets(certificates_fn, env=env, region=region)

        # ── Clients Lambda ─────────────────────────────────────────────────────
        clients_fn = lmb.Function(
            self, "ClientsFunction",
            function_name = f"codelabs-billing-{env}-clients",
            runtime       = lmb.Runtime.PYTHON_3_12,
            architecture  = lmb.Architecture.ARM_64,
            code          = _code,
            handler       = "lambdas.clients.handler.handler",
            timeout       = Duration.seconds(15),
            memory_size   = 256,
            environment   = {
                **_common_env,
                "CLIENTS_TABLE":     database.clients_table.table_name,
                "AUDIT_LOG_TABLE":   database.audit_table.table_name,
                "IDEMPOTENCY_TABLE": database.idempotency_table.table_name,
            },
        )
        database.clients_table.grant_read_write_data(clients_fn)
        database.audit_table.grant_read_write_data(clients_fn)
        database.idempotency_table.grant_read_write_data(clients_fn)

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
                "OUTBOX_TABLE":                  database.outbox_table.table_name,
                "EVENTS_QUEUE_URL":              queues.tenant_onboarding_queue.queue_url,
                "EMAIL_NOTIFICATIONS_QUEUE_URL": queues.email_notifications_queue.queue_url,
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
        queues.email_notifications_queue.grant_send_messages(outbox_relay_fn)
        queues.email_notifications_key.grant_encrypt_decrypt(outbox_relay_fn)

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
                "SUPERADMIN_EMAIL":   config.get("superadmin_email", ""),
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

        # ── Migrations Worker ─────────────────────────────────────────────────
        # Invocado por CI/CD después del deploy de API. Registra ejecuciones en
        # MIGRATIONS_TABLE para que cada migración de datos corra una sola vez.
        migrations_fn = lmb.Function(
            self, "MigrationsFunction",
            function_name = f"codelabs-billing-{env}-migrations",
            runtime       = lmb.Runtime.PYTHON_3_12,
            architecture  = lmb.Architecture.ARM_64,
            code          = _code,
            handler       = "lambdas.workers.migrations.handler.handler",
            timeout       = Duration.seconds(60),
            memory_size   = 256,
            environment   = {
                **_common_env,
                "MIGRATIONS_TABLE": database.migrations_table.table_name,
                "PLANS_TABLE":      database.plans_table.table_name,
                "TENANTS_TABLE":    database.tenants_table.table_name,
            },
        )
        database.migrations_table.grant_read_write_data(migrations_fn)
        database.plans_table.grant_read_write_data(migrations_fn)
        database.tenants_table.grant_read_write_data(migrations_fn)

        # ── Certificate Expiry Notifier Worker ────────────────────────────────
        # Corre diario via EventBridge: alerta a los tenants 60 y 30 dias antes
        # de que venza su certificado digital p12.
        certificate_expiry_notifier_fn = lmb.Function(
            self, "CertificateExpiryNotifierWorker",
            function_name = f"codelabs-billing-{env}-certificate-expiry-notifier",
            runtime       = lmb.Runtime.PYTHON_3_12,
            architecture  = lmb.Architecture.ARM_64,
            code          = _code,
            handler       = "lambdas.workers.certificate_expiry_notifier.handler.handler",
            timeout       = Duration.seconds(60),
            memory_size   = 256,
            environment   = {
                **_common_env,
                "TENANTS_TABLE":      database.tenants_table.table_name,
                "AUDIT_LOG_TABLE":    database.audit_table.table_name,
                "BREVO_SECRET_NAME":  f"codelabs-billing-{env}/brevo-api-key",
                "BREVO_SENDER_EMAIL": "noreply@codelabsecuador.com",
                "BREVO_SENDER_NAME":  "CodeLabs Billing",
            },
        )
        database.tenants_table.grant_read_write_data(certificate_expiry_notifier_fn)
        database.audit_table.grant_read_write_data(certificate_expiry_notifier_fn)
        certificate_expiry_notifier_fn.add_to_role_policy(iam.PolicyStatement(
            actions   = ["secretsmanager:GetSecretValue"],
            resources = [
                f"arn:aws:secretsmanager:{region}:*:secret:codelabs-billing-{env}/brevo-api-key*"
            ],
        ))

        events.Rule(
            self, "CertificateExpiryNotifierSchedule",
            schedule = events.Schedule.expression("cron(0 9 * * ? *)"),
            targets  = [events_targets.LambdaFunction(certificate_expiry_notifier_fn)],
        )

        # ── Subscription Renewal Notifier Worker ──────────────────────────────
        # Corre diario: avisa a los tenants que su suscripcion vence en 7 dias
        # y suspende (expire_subscription) a los que ya vencieron.
        subscription_renewal_notifier_fn = lmb.Function(
            self, "SubscriptionRenewalNotifierWorker",
            function_name = f"codelabs-billing-{env}-subscription-renewal-notifier",
            runtime       = lmb.Runtime.PYTHON_3_12,
            architecture  = lmb.Architecture.ARM_64,
            code          = _code,
            handler       = "lambdas.workers.subscription_renewal_notifier.handler.handler",
            timeout       = Duration.seconds(60),
            memory_size   = 256,
            environment   = {
                **_common_env,
                "TENANTS_TABLE":      database.tenants_table.table_name,
                "AUDIT_LOG_TABLE":    database.audit_table.table_name,
                "BREVO_SECRET_NAME":  f"codelabs-billing-{env}/brevo-api-key",
                "BREVO_SENDER_EMAIL": "noreply@codelabsecuador.com",
                "BREVO_SENDER_NAME":  "CodeLabs Billing",
                "FRONTEND_URL":       frontend_url,
            },
        )
        database.tenants_table.grant_read_write_data(subscription_renewal_notifier_fn)
        database.audit_table.grant_read_write_data(subscription_renewal_notifier_fn)
        subscription_renewal_notifier_fn.add_to_role_policy(iam.PolicyStatement(
            actions   = ["secretsmanager:GetSecretValue"],
            resources = [
                f"arn:aws:secretsmanager:{region}:*:secret:codelabs-billing-{env}/brevo-api-key*"
            ],
        ))

        events.Rule(
            self, "SubscriptionRenewalNotifierSchedule",
            schedule = events.Schedule.expression("cron(0 10 * * ? *)"),
            targets  = [events_targets.LambdaFunction(subscription_renewal_notifier_fn)],
        )

        # ── Orphan Payment Notifier Worker ────────────────────────────────────
        # Corre cada hora: detecta pagos PAID sin tenant vinculado (pago flotante)
        # y alerta al superadmin para recuperacion manual.
        orphan_payment_notifier_fn = lmb.Function(
            self, "OrphanPaymentNotifierWorker",
            function_name = f"codelabs-billing-{env}-orphan-payment-notifier",
            runtime       = lmb.Runtime.PYTHON_3_12,
            architecture  = lmb.Architecture.ARM_64,
            code          = _code,
            handler       = "lambdas.workers.orphan_payment_notifier.handler.handler",
            timeout       = Duration.seconds(60),
            memory_size   = 256,
            environment   = {
                **_common_env,
                "PAYMENTS_TABLE":               database.payments_table.table_name,
                "BREVO_SECRET_NAME":            f"codelabs-billing-{env}/brevo-api-key",
                "BREVO_SENDER_EMAIL":           "noreply@codelabsecuador.com",
                "BREVO_SENDER_NAME":            "CodeLabs Billing",
                "SUPERADMIN_EMAIL":             config.get("superadmin_email", ""),
                "ORPHAN_PAYMENT_GRACE_MINUTES": "30",
            },
        )
        database.payments_table.grant_read_data(orphan_payment_notifier_fn)
        orphan_payment_notifier_fn.add_to_role_policy(iam.PolicyStatement(
            actions   = ["secretsmanager:GetSecretValue"],
            resources = [
                f"arn:aws:secretsmanager:{region}:*:secret:codelabs-billing-{env}/brevo-api-key*"
            ],
        ))

        events.Rule(
            self, "OrphanPaymentNotifierSchedule",
            schedule = events.Schedule.expression("cron(0 * * * ? *)"),
            targets  = [events_targets.LambdaFunction(orphan_payment_notifier_fn)],
        )

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
            (apigwv2.HttpMethod.POST,   "/tenants/{id}/onboarding/retry"),
            (apigwv2.HttpMethod.POST,   "/tenants/{id}/subscription/activate"),
            (apigwv2.HttpMethod.POST,   "/tenants/{id}/subscription/renew"),
            (apigwv2.HttpMethod.DELETE, "/tenants/{id}"),
        ]:
            api.add_routes(
                path        = route,
                methods     = [method],
                integration = tenants_integration,
                authorizer  = jwt_authorizer,
            )

        certificates_integration = integrations.HttpLambdaIntegration(
            "CertificatesIntegration", certificates_fn
        )

        for method, route in [
            (apigwv2.HttpMethod.GET, "/tenants/{id}/certificate"),
            (apigwv2.HttpMethod.PUT, "/tenants/{id}/certificate"),
        ]:
            api.add_routes(
                path        = route,
                methods     = [method],
                integration = certificates_integration,
                authorizer  = jwt_authorizer,
            )

        clients_integration = integrations.HttpLambdaIntegration(
            "ClientsIntegration", clients_fn
        )

        for method, route in [
            (apigwv2.HttpMethod.POST,   "/clients"),
            (apigwv2.HttpMethod.GET,    "/clients"),
            (apigwv2.HttpMethod.GET,    "/clients/{id}"),
            (apigwv2.HttpMethod.PATCH,  "/clients/{id}"),
            (apigwv2.HttpMethod.DELETE, "/clients/{id}"),
        ]:
            api.add_routes(
                path        = route,
                methods     = [method],
                integration = clients_integration,
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

        # POST / PATCH / admin GETs requieren superadmin
        for method, route in [
            (apigwv2.HttpMethod.GET,   "/superadmin/plans"),
            (apigwv2.HttpMethod.GET,   "/superadmin/plans/{id}"),
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

        # ── Onboarding Lambda (registro self-service público) ──────────────────
        onboarding_api_fn = lmb.Function(
            self, "OnboardingApiFunction",
            function_name = f"codelabs-billing-{env}-onboarding",
            runtime       = lmb.Runtime.PYTHON_3_12,
            architecture  = lmb.Architecture.ARM_64,
            code          = _code,
            handler       = "lambdas.onboarding.handler.handler",
            timeout       = Duration.seconds(30),
            memory_size   = 256,
            environment   = {
                **_common_env,
                "TENANTS_TABLE":     database.tenants_table.table_name,
                "PLANS_TABLE":       database.plans_table.table_name,
                "PAYMENTS_TABLE":    database.payments_table.table_name,
                "AUDIT_LOG_TABLE":   database.audit_table.table_name,
                "IDEMPOTENCY_TABLE": database.idempotency_table.table_name,
                "OUTBOX_TABLE":      database.outbox_table.table_name,
                "CERTIFICATE_SECRET_PREFIX": f"/codelabs-billing/{env}/tenant",
            },
        )
        database.tenants_table.grant_read_write_data(onboarding_api_fn)
        database.plans_table.grant_read_data(onboarding_api_fn)
        database.payments_table.grant_read_write_data(onboarding_api_fn)
        database.audit_table.grant_read_write_data(onboarding_api_fn)
        database.idempotency_table.grant_read_write_data(onboarding_api_fn)
        database.outbox_table.grant_write_data(onboarding_api_fn)
        self._grant_certificate_secrets(
            onboarding_api_fn, env=env, region=region, allow_delete=True
        )

        onboarding_integration = integrations.HttpLambdaIntegration(
            "OnboardingIntegration", onboarding_api_fn
        )

        # Público por diseño: registro self-service con OTP, sin JWT.
        onboarding_routes: list[apigwv2.HttpRoute] = []
        for route in ["/onboarding/otp/request", "/onboarding/otp/confirm"]:
            onboarding_routes.extend(api.add_routes(
                path        = route,
                methods     = [apigwv2.HttpMethod.POST],
                integration = onboarding_integration,
            ))

        # ── Subscriptions Lambda (dLocal Go SmartFields — pagos por plan) ──────
        subscriptions_fn = lmb.Function(
            self, "SubscriptionsFunction",
            function_name = f"codelabs-billing-{env}-subscriptions",
            runtime       = lmb.Runtime.PYTHON_3_12,
            architecture  = lmb.Architecture.ARM_64,
            code          = _code,
            handler       = "lambdas.subscriptions.handler.handler",
            timeout       = Duration.seconds(15),
            memory_size   = 256,
            environment   = {
                **_common_env,
                "PAYMENTS_TABLE":             database.payments_table.table_name,
                "PLANS_TABLE":                database.plans_table.table_name,
                "IDEMPOTENCY_TABLE":          database.idempotency_table.table_name,
                "DLOCALGO_CREDENTIALS_NAME":  f"codelabs-billing-{env}/dlocalgo-credentials",
                "DLOCALGO_API_URL":           "https://api.dlocalgo.com" if env == "prod" else "https://api-sbx.dlocalgo.com",
            },
        )
        database.payments_table.grant_read_write_data(subscriptions_fn)
        database.plans_table.grant_read_data(subscriptions_fn)
        database.idempotency_table.grant_read_write_data(subscriptions_fn)
        subscriptions_fn.add_to_role_policy(iam.PolicyStatement(
            actions   = ["secretsmanager:GetSecretValue"],
            resources = [
                f"arn:aws:secretsmanager:{region}:*:secret:codelabs-billing-{env}/dlocalgo-credentials*"
            ],
        ))

        subscriptions_integration = integrations.HttpLambdaIntegration(
            "SubscriptionsIntegration", subscriptions_fn
        )

        # Público por diseño: el pago y confirmación ocurren antes o durante onboarding.
        subscriptions_routes: list[apigwv2.HttpRoute] = []
        subscriptions_routes.extend(api.add_routes(
            path        = "/subscriptions/payments",
            methods     = [apigwv2.HttpMethod.POST],
            integration = subscriptions_integration,
        ))
        subscriptions_routes.extend(api.add_routes(
            path        = "/subscriptions/payments/{order_id}/confirm",
            methods     = [apigwv2.HttpMethod.POST],
            integration = subscriptions_integration,
        ))
        subscriptions_routes.extend(api.add_routes(
            path        = "/subscriptions/payments/{order_id}",
            methods     = [apigwv2.HttpMethod.GET],
            integration = subscriptions_integration,
        ))
        # Refund — superadmin únicamente; requiere JWT para que API Gateway valide el token.
        subscriptions_routes.extend(api.add_routes(
            path        = "/subscriptions/payments/{order_id}/refund",
            methods     = [apigwv2.HttpMethod.POST],
            integration = subscriptions_integration,
            authorizer  = jwt_authorizer,
        ))
        # Webhook dLocal Go — público; autenticación vía HMAC-SHA256 en el handler.
        subscriptions_routes.extend(api.add_routes(
            path        = "/subscriptions/webhooks/dlocal",
            methods     = [apigwv2.HttpMethod.POST],
            integration = subscriptions_integration,
        ))

        # ── Throttle de stage — todas las rutas con override por ruta ─────────
        # RouteSettings y DefaultRouteSettings se consolidan aquí, después de que
        # todas las rutas están registradas, para poder usar add_dependency en cada
        # una y evitar el error "Unable to find Route by key" en CloudFormation.
        request_throttle       = throttling_cfg.get("onboarding_otp_request", {})
        confirm_throttle       = throttling_cfg.get("onboarding_otp_confirm", {})
        pay_create_throttle    = throttling_cfg.get("payment_create", {})
        pay_capture_throttle   = throttling_cfg.get("payment_confirm", throttling_cfg.get("payment_capture", {}))
        pay_get_throttle       = throttling_cfg.get("payment_get", {})
        default_throttle       = throttling_cfg.get("default", {})
        if api.default_stage:
            cfn_stage = api.default_stage.node.default_child
            throttled_routes = onboarding_routes + subscriptions_routes
            for route in throttled_routes:
                cfn_stage.add_dependency(route.node.default_child)
            cfn_stage.add_property_override("DefaultRouteSettings", {
                "ThrottlingBurstLimit": default_throttle.get("burst_limit", 20),
                "ThrottlingRateLimit": default_throttle.get("rate_limit", 10),
            })
            cfn_stage.add_property_override("RouteSettings", {
                "POST /onboarding/otp/request": {
                    "ThrottlingBurstLimit": request_throttle.get("burst_limit", 5),
                    "ThrottlingRateLimit": request_throttle.get("rate_limit", 1),
                },
                "POST /onboarding/otp/confirm": {
                    "ThrottlingBurstLimit": confirm_throttle.get("burst_limit", 10),
                    "ThrottlingRateLimit": confirm_throttle.get("rate_limit", 2),
                },
                "POST /subscriptions/payments": {
                    "ThrottlingBurstLimit": pay_create_throttle.get("burst_limit", 5),
                    "ThrottlingRateLimit": pay_create_throttle.get("rate_limit", 2),
                },
                "POST /subscriptions/payments/{order_id}/confirm": {
                    "ThrottlingBurstLimit": pay_capture_throttle.get("burst_limit", 10),
                    "ThrottlingRateLimit": pay_capture_throttle.get("rate_limit", 5),
                },
                "GET /subscriptions/payments/{order_id}": {
                    "ThrottlingBurstLimit": pay_get_throttle.get("burst_limit", 20),
                    "ThrottlingRateLimit": pay_get_throttle.get("rate_limit", 10),
                },
            })

        # ── Outputs ───────────────────────────────────────────────────────────
        CfnOutput(self, "ApiUrl",
                  value       = api.url or "",
                  export_name = f"CodeLabsBilling-{env}-ApiUrl")

        if api_domain:
            CfnOutput(self, "ApiCustomDomain",
                      value       = f"https://{api_domain}",
                      export_name = f"CodeLabsBilling-{env}-ApiCustomDomain")
