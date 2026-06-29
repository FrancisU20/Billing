from __future__ import annotations

import unittest

from pydantic import ValidationError

from lambdas.subscriptions.schemas import ConfirmPaymentRequest


class ConfirmPaymentRequestSchemaTests(unittest.TestCase):
    def _payload(self, *, document_type: str = "CI", document: str = "1710034065") -> dict:
        return {
            "card_token": "card_tok_abc",
            "client_first_name": "Test",
            "client_last_name": "User",
            "client_email": "test@example.com",
            "client_document_type": document_type,
            "client_document": document,
        }

    def test_accepts_valid_cedula(self) -> None:
        req = ConfirmPaymentRequest(**self._payload(document_type="CI", document="1710034065"))
        self.assertEqual(req.client_document, "1710034065")

    def test_accepts_valid_ruc(self) -> None:
        req = ConfirmPaymentRequest(**self._payload(document_type="RUC", document="1790011674001"))
        self.assertEqual(req.client_document, "1790011674001")

    def test_strips_document_before_validating(self) -> None:
        req = ConfirmPaymentRequest(**self._payload(document=" 1710034065 "))
        self.assertEqual(req.client_document, "1710034065")

    def test_rejects_invalid_cedula(self) -> None:
        with self.assertRaises(ValidationError):
            ConfirmPaymentRequest(**self._payload(document_type="CI", document="1712345678"))

    def test_rejects_invalid_ruc(self) -> None:
        with self.assertRaises(ValidationError):
            ConfirmPaymentRequest(**self._payload(document_type="RUC", document="1710034065"))


if __name__ == "__main__":
    unittest.main()
