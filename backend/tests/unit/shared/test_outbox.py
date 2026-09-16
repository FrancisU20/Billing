from __future__ import annotations

import json
import time
import unittest
from dataclasses import dataclass

from shared.domain.events.domain_event import DomainEvent
from shared.domain.events.outbox import outbox_item, outbox_put_transact_item


@dataclass(frozen=True)
class SampleEvent(DomainEvent):
    tenant_id: str = "tenant-1"


@dataclass(frozen=True)
class OnboardingOtpRequestedEvent(DomainEvent):
    tenant_id: str = "tenant-1"


class OutboxItemTests(unittest.TestCase):
    def test_required_fields_present(self) -> None:
        event = SampleEvent()
        item = outbox_item(event, source="test_source")
        for key in (
            "id",
            "status",
            "event_type",
            "source",
            "payload",
            "created_at",
            "updated_at",
            "attempts",
            "ttl",
        ):
            self.assertIn(key, item)

    def test_status_is_pending(self) -> None:
        item = outbox_item(SampleEvent(), source="test_source")
        self.assertEqual(item["status"], "PENDING")

    def test_event_id_matches(self) -> None:
        event = SampleEvent()
        item = outbox_item(event, source="test_source")
        self.assertEqual(item["id"], event.event_id)

    def test_event_type_matches(self) -> None:
        item = outbox_item(SampleEvent(), source="test_source")
        self.assertEqual(item["event_type"], "SampleEvent")

    def test_payload_is_json_string(self) -> None:
        item = outbox_item(SampleEvent(), source="test_source")
        parsed = json.loads(item["payload"])
        self.assertIn("event_type", parsed)
        self.assertIn("data", parsed)

    def test_attempts_starts_at_zero(self) -> None:
        item = outbox_item(SampleEvent(), source="test_source")
        self.assertEqual(item["attempts"], 0)

    def test_ttl_approx_30_days(self) -> None:
        item = outbox_item(SampleEvent(), source="test_source")
        thirty_days = 30 * 24 * 60 * 60
        self.assertAlmostEqual(item["ttl"] - int(time.time()), thirty_days, delta=5)

    def test_otp_event_has_short_ttl(self) -> None:
        item = outbox_item(OnboardingOtpRequestedEvent(), source="test_source")
        one_hour = 60 * 60
        self.assertAlmostEqual(item["ttl"] - int(time.time()), one_hour, delta=5)

    def test_source_stored(self) -> None:
        item = outbox_item(SampleEvent(), source="onboarding_lambda")
        self.assertEqual(item["source"], "onboarding_lambda")


class OutboxPutTransactItemTests(unittest.TestCase):
    def test_wraps_in_put_with_condition(self) -> None:
        event = SampleEvent()
        result = outbox_put_transact_item("outbox-table", event, source="src")
        self.assertIn("Put", result)
        put = result["Put"]
        self.assertEqual(put["TableName"], "outbox-table")
        self.assertIn("ConditionExpression", put)
        self.assertEqual(put["Item"]["id"], event.event_id)

    def test_condition_prevents_duplicate(self) -> None:
        result = outbox_put_transact_item("outbox-table", SampleEvent(), source="src")
        self.assertIn("attribute_not_exists", result["Put"]["ConditionExpression"])


if __name__ == "__main__":
    unittest.main()
