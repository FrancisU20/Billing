from aws_cdk import Stack, Duration, aws_sqs as sqs, aws_events as events, aws_events_targets as targets
from constructs import Construct


class QueuesStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, config: dict, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        env = config["env"]
        sqs_cfg = config["sqs"]
        max_receives = sqs_cfg["max_receive_count"]

        def make_queue(name: str, visibility_timeout_s: int, fifo: bool = False) -> sqs.Queue:
            suffix = ".fifo" if fifo else ""
            dlq = sqs.Queue(
                self, f"{name}Dlq",
                queue_name=f"codelabs-billing-{env}-{name}-dlq{suffix}",
                retention_period=Duration.days(14),
                fifo=fifo,
            )
            return sqs.Queue(
                self, f"{name}Queue",
                queue_name=f"codelabs-billing-{env}-{name}{suffix}",
                visibility_timeout=Duration.seconds(visibility_timeout_s),
                retention_period=Duration.days(4),
                dead_letter_queue=sqs.DeadLetterQueue(max_receive_count=max_receives, queue=dlq),
                fifo=fifo,
                # ContentBasedDeduplication solo aplica a colas FIFO
                **({"content_based_deduplication": True} if fifo else {}),
            )

        # Cola principal de procesamiento de comprobantes (FIFO para deduplicación)
        self.invoice_processing_queue = make_queue(
            "invoice-processing",
            sqs_cfg["invoice_processing_visibility_timeout"],
            fifo=True,
        )

        # Cola de consulta de autorización SRI
        self.sri_authorization_queue = make_queue(
            "sri-authorization",
            sqs_cfg["sri_retry_visibility_timeout"],
        )

        # Cola de envío de correos
        self.email_dispatch_queue = make_queue(
            "email-dispatch",
            sqs_cfg["email_dispatch_visibility_timeout"],
        )

        # Cola de importación de lotes (CSV/Excel)
        self.batch_import_queue = make_queue(
            "batch-import",
            sqs_cfg["batch_import_visibility_timeout"],
        )

        # Cola de onboarding de nuevos tenants (crear usuario Cognito + email bienvenida)
        # Standard — las creaciones son independientes entre sí, orden no importa
        self.tenant_onboarding_queue = make_queue(
            "tenant-onboarding",
            sqs_cfg.get("tenant_onboarding_visibility_timeout", 120),
        )

        # EventBridge rule — scheduler de reintentos automáticos (cada 5 minutos)
        # Consulta comprobantes en RETRY_PENDING y los encola en sri-authorization-queue
        retry_scheduler = events.Rule(
            self, "SriRetryScheduler",
            rule_name=f"codelabs-billing-{env}-sri-retry-scheduler",
            description="Encola comprobantes RETRY_PENDING para reconsulta al SRI",
            schedule=events.Schedule.rate(Duration.minutes(5)),
        )
        retry_scheduler.add_target(
            targets.SqsQueue(
                self.sri_authorization_queue,
                message=events.RuleTargetInput.from_object({"source": "scheduler", "type": "retry_pending"}),
            )
        )
