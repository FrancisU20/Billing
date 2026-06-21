from __future__ import annotations

import unittest

from lambdas.invoice_processor.sri_error_classifier import PERMANENT, RETRYABLE, classify
from lambdas.invoice_processor.sri_error_mapper import normalize_sri_error


class ClassifySriErrorTests(unittest.TestCase):
    def test_known_retryable_code(self) -> None:
        self.assertEqual(classify("70"), RETRYABLE)

    def test_unknown_code_defaults_to_permanent(self) -> None:
        self.assertEqual(classify("999"), PERMANENT)

    def test_empty_code_defaults_to_permanent(self) -> None:
        self.assertEqual(classify(""), PERMANENT)

    def test_normalizes_known_receptor_error(self) -> None:
        error = normalize_sri_error(
            code="069",
            message="ERROR EN LA IDENTIFICACION DEL RECEPTOR",
        )

        self.assertEqual(error["code"], "69")
        self.assertEqual(error["category"], "RECEPTOR")
        self.assertEqual(error["classification"], PERMANENT)
        self.assertIn("9999999999999", error["user_message"])


if __name__ == "__main__":
    unittest.main()
