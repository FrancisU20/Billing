from aws_cdk import Stack, Duration, aws_cloudwatch as cw, aws_logs as logs
from constructs import Construct


class ObservabilityStack(Stack):
    def __init__(
        self, scope: Construct, construct_id: str,
        config: dict, api_stack, queues, **kwargs,
    ):
        super().__init__(scope, construct_id, **kwargs)

        env = config["env"]
        cw_cfg = config["cloudwatch"]

        # Alarma: mensajes en DLQ de invoice processing
        cw.Alarm(
            self, "InvoiceDlqAlarm",
            alarm_name=f"codelabs-billing-{env}-invoice-dlq-messages",
            alarm_description="Comprobantes en DLQ — revisar procesamiento",
            metric=cw.Metric(
                namespace="AWS/SQS",
                metric_name="ApproximateNumberOfMessagesVisible",
                dimensions_map={"QueueName": queues.invoice_processing_queue.queue_name.replace(".fifo", "-dlq.fifo")},
                period=Duration.minutes(5),
                statistic="Sum",
            ),
            threshold=1,
            evaluation_periods=1,
            comparison_operator=cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
            treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
        )

        # Alarma: errores 5xx en API Gateway > 5%
        cw.Alarm(
            self, "ApiGateway5xxAlarm",
            alarm_name=f"codelabs-billing-{env}-api-5xx-errors",
            alarm_description="Errores 5xx en API Gateway superiores al umbral",
            metric=cw.Metric(
                namespace="AWS/ApiGateway",
                metric_name="5XXError",
                dimensions_map={"ApiName": f"codelabs-billing-{env}"},
                period=Duration.minutes(5),
                statistic="Sum",
            ),
            threshold=10,
            evaluation_periods=2,
            treat_missing_data=cw.TreatMissingData.NOT_BREACHING,
        )

        # Dashboard solo si está habilitado en config
        if cw_cfg["custom_dashboards"]:
            cw.Dashboard(
                self, "MainDashboard",
                dashboard_name=f"codelabs-billing-{env}",
                widgets=[
                    [
                        cw.GraphWidget(
                            title="API Gateway — Requests",
                            left=[cw.Metric(
                                namespace="AWS/ApiGateway",
                                metric_name="Count",
                                dimensions_map={"ApiName": f"codelabs-billing-{env}"},
                                period=Duration.minutes(5),
                                statistic="Sum",
                            )],
                            right=[cw.Metric(
                                namespace="AWS/ApiGateway",
                                metric_name="5XXError",
                                dimensions_map={"ApiName": f"codelabs-billing-{env}"},
                                period=Duration.minutes(5),
                                statistic="Sum",
                            )],
                        ),
                        cw.GraphWidget(
                            title="SQS — Mensajes por cola",
                            left=[
                                cw.Metric(
                                    namespace="AWS/SQS",
                                    metric_name="NumberOfMessagesSent",
                                    dimensions_map={"QueueName": queues.invoice_processing_queue.queue_name},
                                    period=Duration.minutes(5),
                                    statistic="Sum",
                                    label="Invoice Processing",
                                ),
                            ],
                        ),
                    ],
                ],
            )
