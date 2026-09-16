from __future__ import annotations

import unittest
from dataclasses import dataclass
from datetime import datetime

from shared.domain.base_entity import GlobalEntity, TenantScopedEntity


@dataclass
class ConcreteGlobal(GlobalEntity):
    pass


@dataclass
class ConcreteTenantScoped(TenantScopedEntity):
    pass


class GlobalEntityTests(unittest.TestCase):
    def test_id_auto_generated(self) -> None:
        e = ConcreteGlobal()
        self.assertIsInstance(e.id, str)
        self.assertTrue(len(e.id) > 0)

    def test_two_instances_have_different_ids(self) -> None:
        self.assertNotEqual(ConcreteGlobal().id, ConcreteGlobal().id)

    def test_defaults(self) -> None:
        e = ConcreteGlobal()
        self.assertEqual(e.version, 1)
        self.assertFalse(e.deleted)
        self.assertIsNone(e.deleted_at)
        self.assertIsNone(e.deleted_by)
        self.assertIsInstance(e.created_at, datetime)
        self.assertIsInstance(e.updated_at, datetime)

    def test_touch_increments_version(self) -> None:
        e = ConcreteGlobal()
        e.touch("user-1")
        self.assertEqual(e.version, 2)

    def test_touch_sets_updated_by(self) -> None:
        e = ConcreteGlobal()
        e.touch("user-1")
        self.assertEqual(e.updated_by, "user-1")

    def test_touch_updates_updated_at(self) -> None:
        e = ConcreteGlobal()
        original = e.updated_at
        e.touch("user-1")
        self.assertGreaterEqual(e.updated_at, original)

    def test_soft_delete_marks_deleted(self) -> None:
        e = ConcreteGlobal()
        e.soft_delete("admin")
        self.assertTrue(e.deleted)
        self.assertEqual(e.deleted_by, "admin")
        self.assertIsNotNone(e.deleted_at)

    def test_soft_delete_also_touches(self) -> None:
        e = ConcreteGlobal()
        e.soft_delete("admin")
        self.assertEqual(e.version, 2)
        self.assertEqual(e.updated_by, "admin")


class TenantScopedEntityTests(unittest.TestCase):
    def test_requires_tenant_id(self) -> None:
        with self.assertRaises(ValueError):
            ConcreteTenantScoped(tenant_id="")

    def test_valid_tenant_id_accepted(self) -> None:
        e = ConcreteTenantScoped(tenant_id="t-123")
        self.assertEqual(e.tenant_id, "t-123")

    def test_inherits_global_entity_defaults(self) -> None:
        e = ConcreteTenantScoped(tenant_id="t-123")
        self.assertEqual(e.version, 1)
        self.assertFalse(e.deleted)

    def test_touch_and_delete_work(self) -> None:
        e = ConcreteTenantScoped(tenant_id="t-123")
        e.touch("user-1")
        self.assertEqual(e.version, 2)
        e.soft_delete("admin")
        self.assertTrue(e.deleted)


if __name__ == "__main__":
    unittest.main()
