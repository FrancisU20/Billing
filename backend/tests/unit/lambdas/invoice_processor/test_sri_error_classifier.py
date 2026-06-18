from __future__ import annotations

import unittest

from lambdas.invoice_processor.sri_error_classifier import PERMANENT, RETRYABLE, classify


class ClassifySriErrorTests(unittest.TestCase):
    def test_known_retryable_code(self) -> None:
        self.assertEqual(classify("70"), RETRYABLE)

    def test_unknown_code_defaults_to_permanent(self) -> None:
        self.assertEqual(classify("999"), PERMANENT)

    def test_empty_code_defaults_to_permanent(self) -> None:
        self.assertEqual(classify(""), PERMANENT)


if __name__ == "__main__":
    unittest.main()
