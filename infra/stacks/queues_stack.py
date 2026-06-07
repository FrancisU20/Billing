"""
QueuesStack — colas SQS del sistema.

Una cola por flujo de trabajo asíncrono.
Cada cola tiene su DLQ para mensajes que fallaron todos los reintentos.

Colas actuales:
  tenant-onboarding    → crea usuario Cognito cuando se registra un tenant
  email-notifications  → envía emails de bienvenida via Brevo (contiene temp_password cifrado)
"""
from aws_cdk import (
    Stack, Duration, CfnOutput,
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
