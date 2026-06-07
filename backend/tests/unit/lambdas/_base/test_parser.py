from __future__ import annotations

import unittest

from lambdas._base.parser import Request
from shared.errors import MissingTenantContextError, ValidationError
from tests.unit.support import api_event


class ParserTests(unittest.TestCase):
    def test_body_hash_is_canonical_for_equivalent_json(self) -> None:
        left = Request.from_event(api_event(
            method="POST",
            path="/tenants",
            body={"a": 1, "b": 2},
        ))
        right = Request.from_event(api_event(
            method="POST",
            path="/tenants",
            body={"b": 2, "a": 1},
        ))

        self.assertEqual(left.body_hash, right.body_hash)

    def test_path_includes_sorted_query_params(self) -> None:
        request = Request.from_event(api_event(
            method="GET",
            path="/tenants",
            query={"z": "last", "a": "first"},
        ))

        self.assertEqual(request.path, "/tenants?a=first&z=last")

    def test_rejects_json_arrays_as_http_body(self) -> None:
        event = api_event(method="POST", path="/tenants")
        event["body"] = "[1, 2, 3]"

        with self.assertRaises(ValidationError):
            Request.from_event(event)

    def test_requires_tenant_claim_for_non_superadmin(self) -> None:
        event = api_event(
            method="GET",
            path="/tenants/tenant-1",
            claims={
                "custom:is_superadmin": "false",
                "custom:tenant_id": "",
                "custom:role": "viewer",
            },
        )

        with self.assertRaises(MissingTenantContextError):
            Request.from_event(event)


if __name__ == "__main__":
    unittest.main()
