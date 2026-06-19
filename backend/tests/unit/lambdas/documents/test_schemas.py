from __future__ import annotations

import unittest

from pydantic import ValidationError

from lambdas.documents.schemas import EmitDocumentRequest


def _emit_body(**overrides):
    base = {
        "establishment_code": "001",
        "emission_point_code": "001",
        "doc_type": "01",
        "issued_at": "2026-06-18",
        "client_id": "client-1",
        "buyer_id_type": "07",
        "buyer_id": "1710034065",
        "buyer_name": "Cliente previo",
        "buyer_email": "buyer@example.com",
        "payment_method": "01",
        "lines": [
            {
                "code": "P001",
                "description": "Producto Test",
                "quantity": "1",
                "unit_price": "10.00",
                "discount": "0.00",
                "iva_rate": "15",
            }
        ],
    }
    base.update(overrides)
    return base


class EmitDocumentRequestSchemaTests(unittest.TestCase):
    def test_normalizes_consumidor_final(self) -> None:
        req = EmitDocumentRequest.model_validate(_emit_body())

        self.assertIsNone(req.client_id)
        self.assertEqual(req.buyer_id_type, "07")
        self.assertEqual(req.buyer_id, "9999999999999")
        self.assertEqual(req.buyer_name, "Consumidor Final")
        self.assertIsNone(req.buyer_email)

    def test_rejects_consumidor_final_id_with_non_consumidor_type(self) -> None:
        with self.assertRaises(ValidationError):
            EmitDocumentRequest.model_validate(
                _emit_body(buyer_id_type="05", buyer_id="9999999999999")
            )

    def test_rejects_discount_above_line_gross(self) -> None:
        with self.assertRaises(ValidationError):
            EmitDocumentRequest.model_validate(
                _emit_body(
                    lines=[
                        {
                            "code": "P001",
                            "description": "Producto Test",
                            "quantity": "1",
                            "unit_price": "10.00",
                            "discount": "10.01",
                            "iva_rate": "15",
                        }
                    ]
                )
            )

    def test_override_requires_reason(self) -> None:
        with self.assertRaises(ValidationError):
            EmitDocumentRequest.model_validate(
                _emit_body(override_discount_ceiling=True, override_reason=None)
            )

    def test_override_rejects_blank_reason(self) -> None:
        with self.assertRaises(ValidationError):
            EmitDocumentRequest.model_validate(
                _emit_body(override_discount_ceiling=True, override_reason="   ")
            )

    def test_override_accepts_a_reason(self) -> None:
        req = EmitDocumentRequest.model_validate(
            _emit_body(
                override_discount_ceiling=True,
                override_reason="Gesto comercial autorizado",
            )
        )

        self.assertTrue(req.override_discount_ceiling)
        self.assertEqual(req.override_reason, "Gesto comercial autorizado")


if __name__ == "__main__":
    unittest.main()
