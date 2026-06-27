from __future__ import annotations

"""
Los emails de documento (autorizado/rechazado/no confirmado/comprador) hardcodeaban
"factura"/"Factura" sin importar el doc_type real — bug real: ya se enviaban sin
filtro de doc_type para Nota de Credito, solo con wording incorrecto. Estos tests
verifican directamente las funciones puras de armado de HTML de
`brevo_email_sender.py` (no hay mocking de HTTP/Brevo necesario).
"""

import importlib
import os
import sys
import unittest

from tests.unit.support import configure_unit_environment

sender = None  # patched in setUpModule — el modulo lee env vars al importarse


def setUpModule() -> None:
    global sender
    configure_unit_environment()
    os.environ.setdefault("BREVO_SECRET_NAME", "dummy-secret")
    sys.modules.pop("lambdas.workers.email_notifications.infra.brevo_email_sender", None)
    sender = importlib.import_module("lambdas.workers.email_notifications.infra.brevo_email_sender")


class DocTypeLabelTests(unittest.TestCase):
    def test_doc_type_01_is_factura(self) -> None:
        self.assertEqual(sender._doc_type_label("01"), "Factura")

    def test_doc_type_04_is_nota_de_credito(self) -> None:
        self.assertEqual(sender._doc_type_label("04"), "Nota de Crédito")


class DocumentAuthorizedWordingTests(unittest.TestCase):
    def _build(self, doc_type: str) -> str:
        return sender._build_document_authorized_html(
            "Juan Pérez",
            "doc-1",
            doc_type,
            "12345",
            "AUTH-1",
            "Mi Empresa",
            "1792146739001",
            "Cliente",
            "1713328506",
            "cliente@example.com",
            "001-001-000000001",
            "2026-06-26",
            "2026-06-26T10:00:00-05:00",
            "100.00",
            "USD",
        )

    def test_factura_says_factura_not_nota_de_credito(self) -> None:
        html = self._build("01")
        self.assertIn("Factura autorizada", html)
        self.assertNotIn("Nota de Crédito", html)

    def test_nota_de_credito_says_nota_de_credito_not_factura(self) -> None:
        html = self._build("04")
        self.assertIn("Nota de Crédito autorizada", html)
        self.assertNotIn(">Factura<", html)


class DocumentRejectedWordingTests(unittest.TestCase):
    def test_nota_de_credito_wording(self) -> None:
        html = sender._build_document_rejected_html("Juan Pérez", "04", "12345", [])
        self.assertIn("nota de crédito", html)
        self.assertNotIn("la factura", html)


class DocumentFailedPermanentWordingTests(unittest.TestCase):
    def test_nota_de_credito_wording(self) -> None:
        html = sender._build_document_failed_permanent_html("Juan Pérez", "04", "12345")
        self.assertIn("nota de crédito", html)
        self.assertNotIn("la factura", html)


class DocumentBuyerWordingTests(unittest.TestCase):
    def test_nota_de_credito_wording(self) -> None:
        html = sender._build_document_buyer_html(
            "Cliente",
            "1713328506",
            "04",
            "12345",
            "AUTH-1",
            "Mi Empresa",
            "1792146739001",
            "2026-06-26",
            "2026-06-26T10:00:00-05:00",
            "100.00",
            "USD",
        )
        self.assertIn("Nota de Crédito", html)
        self.assertNotIn(">Factura<", html)


if __name__ == "__main__":
    unittest.main()
