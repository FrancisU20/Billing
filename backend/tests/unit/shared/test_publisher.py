from __future__ import annotations

import unittest
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum

from shared.domain.events.domain_event import DomainEvent
from shared.domain.events.publisher import _serialize_value, event_payload


class Color(Enum):
    RED = "red"


@dataclass(frozen=True)
class RichEvent(DomainEvent):
    tenant_id: str = "t1"
    amount: Decimal = Decimal("12.50")
    color: Color = Color.RED
    tags: list = None

    def __post_init__(self):
        object.__setattr__(self, "tags", self.tags or ["a", "b"])


class SerializeValueTests(unittest.TestCase):
    def test_enum_returns_value(self) -> None:
        self.assertEqual(_serialize_value(Color.RED), "red")

    def test_decimal_returns_string(self) -> None:
        self.assertEqual(_serialize_value(Decimal("9.99")), "9.99")

    def test_datetime_returns_iso(self) -> None:
        dt = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
        self.assertEqual(_serialize_value(dt), "2024-01-15T12:00:00+00:00")

    def test_list_recursed(self) -> None:
        result = _serialize_value([Decimal("1.0"), Color.RED])
        self.assertEqual(result, ["1.0", "red"])

    def test_dict_recursed(self) -> None:
        result = _serialize_value({"amount": Decimal("5.00")})
        self.assertEqual(result, {"amount": "5.00"})

    def test_plain_string_passthrough(self) -> None:
        self.assertEqual(_serialize_value("hello"), "hello")

    def test_int_passthrough(self) -> None:
        self.assertEqual(_serialize_value(42), 42)

    def test_none_passthrough(self) -> None:
        self.assertIsNone(_serialize_value(None))


class EventPayloadTests(unittest.TestCase):
    def test_top_level_keys(self) -> None:
        event = RichEvent()
        payload = event_payload(event)
        self.assertIn("event_type", payload)
        self.assertIn("event_id", payload)
        self.assertIn("occurred_at", payload)
        self.assertIn("data", payload)

    def test_event_id_and_occurred_at_excluded_from_data(self) -> None:
        event = RichEvent()
        payload = event_payload(event)
        self.assertNotIn("event_id", payload["data"])
        self.assertNotIn("occurred_at", payload["data"])

    def test_event_type_is_class_name(self) -> None:
        payload = event_payload(RichEvent())
        self.assertEqual(payload["event_type"], "RichEvent")

    def test_decimal_serialized_to_string_in_data(self) -> None:
        payload = event_payload(RichEvent())
        self.assertEqual(payload["data"]["amount"], "12.50")

    def test_enum_serialized_in_data(self) -> None:
        payload = event_payload(RichEvent())
        self.assertEqual(payload["data"]["color"], "red")

    def test_occurred_at_is_iso_string(self) -> None:
        payload = event_payload(RichEvent())
        self.assertIsInstance(payload["occurred_at"], str)


if __name__ == "__main__":
    unittest.main()
