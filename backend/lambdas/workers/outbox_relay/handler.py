from __future__ import annotations

"""
Worker: outbox relay.

Triggered by the DynamoDB Stream of the outbox table. Publishes pending events
to SQS and marks each record as PUBLISHED. SQS and Lambda are at-least-once, so
consumers must be idempotent.
"""

from datetime import UTC, datetime

import boto3
from boto3.dynamodb.types import TypeDeserializer
from botocore.exceptions import ClientError

from shared.config import env
from shared.logger import bind_invocation_context, clear_invocation_context, get_logger

_log = get_logger(__name__)
_deserializer = TypeDeserializer()
_sqs = boto3.client("sqs")
_outbox_table = boto3.resource("dynamodb").Table(env("OUTBOX_TABLE"))
_tenant_onboarding_queue_url = env("EVENTS_QUEUE_URL")
_email_notifications_queue_url = env("EMAIL_NOTIFICATIONS_QUEUE_URL")


def _deserialize(image: dict) -> dict:
    return {key: _deserializer.deserialize(value) for key, value in image.items()}


def _queue_for(event_type: str) -> str:
    if event_type == "TenantCreatedEvent":
        return _tenant_onboarding_queue_url
    if event_type == "EnterpriseLeadCreatedEvent":
        return _email_notifications_queue_url
    return ""


def _publish(item: dict) -> bool:
    queue_url = _queue_for(item.get("event_type", ""))
    if not queue_url:
        _log.warning("outbox event has no queue configured", event_type=item.get("event_type"))
        return False

    payload = item["payload"]
    event_type = item["event_type"]
    _sqs.send_message(
        QueueUrl=queue_url,
        MessageBody=payload,
        MessageAttributes={
            "event_type": {
                "StringValue": event_type,
                "DataType": "String",
            }
        },
    )
    return True


def _mark_published(item: dict) -> None:
    # Retry up to 3 times on transient DynamoDB errors (throttle, timeout).
    # If _mark_published fails after SQS send_message succeeded, Lambda retries
    # the stream record and sends the message again (at-least-once delivery).
    # Retrying here reduces the duplicate window without adding external dependencies.
    last_exc: ClientError | None = None
    for attempt in range(3):
        try:
            _outbox_table.update_item(
                Key={"id": item["id"]},
                UpdateExpression=(
                    "SET #status = :published, published_at = :published_at, "
                    "updated_at = :updated_at ADD attempts :one"
                ),
                ConditionExpression="#status = :pending",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":published": "PUBLISHED",
                    ":pending": "PENDING",
                    ":published_at": datetime.now(UTC).isoformat(),
                    ":updated_at": datetime.now(UTC).isoformat(),
                    ":one": 1,
                },
            )
            return
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                _log.info("outbox event already processed", event_id=item.get("id"))
                return
            last_exc = exc
            _log.warning("_mark_published transient error", attempt=attempt + 1, error=str(exc))
    raise last_exc  # type: ignore[misc]


def _mark_skipped(item: dict) -> None:
    try:
        now = datetime.now(UTC).isoformat()
        _outbox_table.update_item(
            Key={"id": item["id"]},
            UpdateExpression=(
                "SET #status = :skipped, skipped_at = :skipped_at, updated_at = :updated_at"
            ),
            ConditionExpression="#status = :pending",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":skipped": "SKIPPED",
                ":pending": "PENDING",
                ":skipped_at": now,
                ":updated_at": now,
            },
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
            _log.info("outbox event already processed", event_id=item.get("id"))
            return
        raise


def handler(event: dict, context) -> dict:
    clear_invocation_context()
    bind_invocation_context(lambda_name=getattr(context, "function_name", "local"))

    failures = []
    for record in event.get("Records", []):
        item_identifier = record.get("dynamodb", {}).get("SequenceNumber") or record.get(
            "eventID", ""
        )
        bind_invocation_context(stream_item_identifier=item_identifier)
        try:
            if record.get("eventName") not in ("INSERT", "MODIFY"):
                continue
            image = record.get("dynamodb", {}).get("NewImage")
            if not image:
                continue
            item = _deserialize(image)
            if item.get("status") != "PENDING":
                continue

            if _publish(item):
                # At-least-once: if _mark_published fails (throttle, timeout) after
                # SQS send_message succeeds, Lambda retries the stream record and sends
                # the message again. All downstream workers MUST be idempotent.
                _mark_published(item)
                _log.info(
                    "outbox event published",
                    event_id=item.get("id"),
                    event_type=item.get("event_type"),
                )
            else:
                _mark_skipped(item)
                _log.info(
                    "outbox event skipped",
                    event_id=item.get("id"),
                    event_type=item.get("event_type"),
                )

        except Exception as exc:
            _log.error("outbox relay error", error=str(exc), exc_info=True)
            failures.append({"itemIdentifier": item_identifier})

    return {"batchItemFailures": failures}
