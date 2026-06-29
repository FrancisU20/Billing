from __future__ import annotations

import unittest
from enum import StrEnum

from lambdas._base.query_params import parse_enum_query_param, parse_list_limit
from shared.db.limits import DEFAULT_LIST_LIMIT, MAX_LIST_LIMIT
from shared.errors import ValidationError


class SampleStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class QueryParamsTests(unittest.TestCase):
    def test_parse_list_limit_uses_default(self) -> None:
        self.assertEqual(parse_list_limit({}), DEFAULT_LIST_LIMIT)

    def test_parse_list_limit_clamps_to_max(self) -> None:
        self.assertEqual(parse_list_limit({"limit": str(MAX_LIST_LIMIT + 1)}), MAX_LIST_LIMIT)

    def test_parse_list_limit_rejects_non_integer(self) -> None:
        with self.assertRaises(ValidationError) as cm:
            parse_list_limit({"limit": "abc"})
        self.assertEqual(cm.exception.detail, "limit debe ser un número entero")

    def test_parse_list_limit_rejects_zero(self) -> None:
        with self.assertRaises(ValidationError) as cm:
            parse_list_limit({"limit": "0"})
        self.assertEqual(cm.exception.detail, "limit debe ser mayor a cero")

    def test_parse_enum_query_param_returns_valid_raw_value(self) -> None:
        result = parse_enum_query_param(
            {"status": "active"},
            "status",
            SampleStatus,
            error_message="Estado inválido",
        )

        self.assertEqual(result, "active")

    def test_parse_enum_query_param_rejects_invalid_value(self) -> None:
        with self.assertRaises(ValidationError) as cm:
            parse_enum_query_param(
                {"status": "unknown"},
                "status",
                SampleStatus,
                error_message="Estado inválido",
            )
        self.assertEqual(cm.exception.detail, "Estado inválido")

    def test_parse_enum_query_param_ignores_missing_value(self) -> None:
        self.assertIsNone(
            parse_enum_query_param(
                {},
                "status",
                SampleStatus,
                error_message="Estado inválido",
            )
        )


if __name__ == "__main__":
    unittest.main()
