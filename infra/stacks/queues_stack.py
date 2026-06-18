"""
QueuesStack — colas SQS del sistema.

Una cola por flujo de trabajo asíncrono.
Cada cola tiene su DLQ para mensajes que fallaron todos los reintentos.

Colas actuales:
  tenant-onboarding    → crea usuario Cognito cuando se registra un tenant
  email-notifications  → envía emails de bienvenida via Brevo (contiene temp_password cifrado)
  invoice-sign         → firma XAdES-BES + envío SRI (compartida, clientes pequeños)
  invoice-poll         → polling de autorización SRI (compartida, clientes pequeños)

Colas enterprise dedicadas (invoice-sign-{tenant_id}, invoice-poll-{tenant_id}):
  Se crean en runtime via POST /tenants/{id}/dedicated-queue/provision (no CDK).
  batch_size=50 en ESM para agrupar 50 docs del mismo RUC en 1 llamada SOAP.
"""
from aws_cdk import (
    Stack, Duration, CfnOutput,
    aws_cloudwatch as cw,
    aws_kms as kms,
    aws_sqs as sqs,
)
from constructs import Construct


class QueuesStack(Stack):
    def __init__(
        self,
        scope:        Construct,
        construct_id: str,
        config:       dict,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        env = config["env"]

        # ── Tenant Onboarding ─────────────────────────────────────────────────
        # Triggered por TenantCreatedEvent — crea usuario owner en Cognito
        tenant_onboarding_dlq = sqs.Queue(
            self, "TenantOnboardingDlq",
            queue_name       = f"codelabs-billing-{env}-tenant-onboarding-dlq",
            retention_period = Duration.days(14),
        )
        self.tenant_onboarding_queue = sqs.Queue(
            self, "TenantOnboardingQueue",
            queue_name         = f"codelabs-billing-{env}-tenant-onboarding",
            visibility_timeout = Duration.seconds(360),  # 6× timeout worker (60s)
            retention_period   = Duration.days(4),
            dead_letter_queue  = sqs.DeadLetterQueue(
                max_receive_count = 3,
                queue             = tenant_onboarding_dlq,
            ),
        )

        # ── Email Notifications ───────────────────────────────────────────────
        # Triggered por OwnerCreatedEvent — contiene temp_password cifrado
        # SSE con CMK propio para control de acceso granular sobre datos sensibles
        email_notifications_key = kms.Key(
            self, "EmailNotificationsKey",
            description         = f"CMK para cola email-notifications ({env})",
            enable_key_rotation = True,
            alias               = f"alias/codelabs-billing-{env}-email-notifications",
        )
        email_notifications_dlq = sqs.Queue(
            self, "EmailNotificationsDlq",
            queue_name        = f"codelabs-billing-{env}-email-notifications-dlq",
            retention_period  = Duration.days(14),
            encryption        = sqs.QueueEncryption.KMS,
            encryption_master_key = email_notifications_key,
        )
        self.email_notifications_queue = sqs.Queue(
            self, "EmailNotificationsQueue",
            queue_name         = f"codelabs-billing-{env}-email-notifications",
            visibility_timeout = Duration.seconds(180),  # 6× timeout worker (30s)
            retention_period   = Duration.days(1),       # mensajes corta vida
            encryption         = sqs.QueueEncryption.KMS,
            encryption_master_key = email_notifications_key,
            dead_letter_queue  = sqs.DeadLetterQueue(
                max_receive_count = 3,
                queue             = email_notifications_dlq,
            ),
        )
        # Exponer la clave para que los Lambdas puedan hacer grant
        self.email_notifications_key = email_notifications_key

        # ── CloudWatch Alarms — DLQ ───────────────────────────────────────────
        # Un mensaje en DLQ = 3 reintentos agotados = fallo permanente de entrega.
        # La alarma dispara cuando hay ≥1 mensaje visible para notificar al equipo.
        cw.Alarm(
            self, "TenantOnboardingDlqAlarm",
            alarm_name        = f"codelabs-billing-{env}-tenant-onboarding-dlq-messages",
            alarm_description = "Mensajes en DLQ de tenant-onboarding: el onboarding falló permanentemente.",
            metric            = tenant_onboarding_dlq.metric_approximate_number_of_messages_visible(
                period=Duration.minutes(1),
            ),
            threshold          = 1,
            evaluation_periods = 1,
            comparison_operator = cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
        )
        cw.Alarm(
            self, "EmailNotificationsDlqAlarm",
            alarm_name        = f"codelabs-billing-{env}-email-notifications-dlq-messages",
            alarm_description = "Mensajes en DLQ de email-notifications: el email de bienvenida falló permanentemente.",
            metric            = email_notifications_dlq.metric_approximate_number_of_messages_visible(
                period=Duration.minutes(1),
            ),
            threshold          = 1,
            evaluation_periods = 1,
            comparison_operator = cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
        )

        # ── Invoice Sign (compartida, clientes pequeños) ──────────────────────
        # Firma XAdES-BES + envío batch al SRI (RecepcionComprobantesOffline).
        # batch_size=10 en ESM; reserved_concurrency=30 en Lambda (ApiStack).
        # Separada de invoice-poll: los POLL son >90% del volumen post-primer-día y
        # saturarían los slots de concurrencia de los SIGN si convivieran.
        # Visibility timeout = 6 × Lambda timeout (60s) = 360s.
        invoice_sign_dlq = sqs.Queue(
            self, "InvoiceSignDlq",
            queue_name       = f"codelabs-billing-{env}-invoice-sign-dlq",
            retention_period = Duration.days(14),
        )
        self.invoice_sign_queue = sqs.Queue(
            self, "InvoiceSignQueue",
            queue_name         = f"codelabs-billing-{env}-invoice-sign",
            visibility_timeout = Duration.seconds(360),
            retention_period   = Duration.days(4),
            dead_letter_queue  = sqs.DeadLetterQueue(
                max_receive_count = 5,
                queue             = invoice_sign_dlq,
            ),
        )

        # ── Invoice Poll (compartida, clientes pequeños) ──────────────────────
        # Consultas de autorización al SRI (AutorizacionComprobantesOffline).
        # AutorizacionComprobantesOffline acepta un solo claveAcceso por llamada —
        # no hay batching posible para POLL. batch_size=10 en ESM; reserved_concurrency=20.
        # Visibility timeout = 6 × Lambda timeout (60s) = 360s.
        invoice_poll_dlq = sqs.Queue(
            self, "InvoicePollDlq",
            queue_name       = f"codelabs-billing-{env}-invoice-poll-dlq",
            retention_period = Duration.days(14),
        )
        self.invoice_poll_queue = sqs.Queue(
            self, "InvoicePollQueue",
            queue_name         = f"codelabs-billing-{env}-invoice-poll",
            visibility_timeout = Duration.seconds(360),
            retention_period   = Duration.days(4),
            dead_letter_queue  = sqs.DeadLetterQueue(
                max_receive_count = 5,
                queue             = invoice_poll_dlq,
            ),
        )

        # ── CloudWatch Alarms — Invoice DLQs ─────────────────────────────────
        cw.Alarm(
            self, "InvoiceSignDlqAlarm",
            alarm_name        = f"codelabs-billing-{env}-invoice-sign-dlq-messages",
            alarm_description = "Mensajes en DLQ invoice-sign: firma o envío SRI falló permanentemente (5 intentos).",
            metric            = invoice_sign_dlq.metric_approximate_number_of_messages_visible(
                period=Duration.minutes(1),
            ),
            threshold           = 1,
            evaluation_periods  = 1,
            comparison_operator = cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
        )
        cw.Alarm(
            self, "InvoicePollDlqAlarm",
            alarm_name        = f"codelabs-billing-{env}-invoice-poll-dlq-messages",
            alarm_description = "Mensajes en DLQ invoice-poll: polling de autorización SRI falló permanentemente (5 intentos).",
            metric            = invoice_poll_dlq.metric_approximate_number_of_messages_visible(
                period=Duration.minutes(1),
            ),
            threshold           = 1,
            evaluation_periods  = 1,
            comparison_operator = cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
        )

        # ── Outputs ───────────────────────────────────────────────────────────
        CfnOutput(self, "TenantOnboardingQueueUrl",
                  value       = self.tenant_onboarding_queue.queue_url,
                  export_name = f"CodeLabsBilling-{env}-TenantOnboardingQueueUrl")

        CfnOutput(self, "TenantOnboardingQueueArn",
                  value       = self.tenant_onboarding_queue.queue_arn,
                  export_name = f"CodeLabsBilling-{env}-TenantOnboardingQueueArn")

        CfnOutput(self, "EmailNotificationsQueueUrl",
                  value       = self.email_notifications_queue.queue_url,
                  export_name = f"CodeLabsBilling-{env}-EmailNotificationsQueueUrl")

        CfnOutput(self, "InvoiceSignQueueUrl",
                  value       = self.invoice_sign_queue.queue_url,
                  export_name = f"CodeLabsBilling-{env}-InvoiceSignQueueUrl")

        CfnOutput(self, "InvoiceSignQueueArn",
                  value       = self.invoice_sign_queue.queue_arn,
                  export_name = f"CodeLabsBilling-{env}-InvoiceSignQueueArn")

        CfnOutput(self, "InvoicePollQueueUrl",
                  value       = self.invoice_poll_queue.queue_url,
                  export_name = f"CodeLabsBilling-{env}-InvoicePollQueueUrl")

        CfnOutput(self, "InvoicePollQueueArn",
                  value       = self.invoice_poll_queue.queue_arn,
                  export_name = f"CodeLabsBilling-{env}-InvoicePollQueueArn")
