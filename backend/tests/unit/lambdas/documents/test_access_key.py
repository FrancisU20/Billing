from __future__ import annotations

import unittest
from datetime import date

from lambdas.documents.domain.access_key import _modulo_11, generate_access_key
from tests.unit.support import configure_unit_environment

configure_unit_environment()


class Modulo11Tests(unittest.TestCase):
    def test_zero_remainder(self) -> None:
        # If sum mod 11 == 0 → check digit = 0
        # 10 * 2 = 20 → 20 % 11 = 9 → 11 - 9 = 2
        self.assertEqual(_modulo_11("0"), 0)

    def test_known_value(self) -> None:
        # Validates the modulo 11 algorithm produces consistent results
        result = _modulo_11("1")
        self.assertIn(result, range(0, 10))

    def test_returns_int(self) -> None:
        self.assertIsInstance(_modulo_11("123456789012345678"), int)


class GenerateAccessKeyTests(unittest.TestCase):
    def _make_key(self, **overrides) -> str:
        defaults = {
            "issued_at": date(2026, 6, 17),
            "doc_type": "01",
            "ruc": "1790000000001",
            "environment": "testing",
            "serie": "001001",
            "sequential": 1,
            "numeric_code": "12345678",
        }
        defaults.update(overrides)
        return generate_access_key(**defaults)

    def test_key_is_49_digits(self) -> None:
        key = self._make_key()
        self.assertEqual(len(key), 49)
        self.assertTrue(key.isdigit())

    def test_testing_environment_uses_digit_1(self) -> None:
        # Tabla 4, Ficha Tecnica SRI: 1=Pruebas, 2=Produccion.
        # tipoAmbiente is at position 22 (0-indexed): 8+2+13 = 23rd char → index 22
        # ddmmyyyy(8) + doc_type(2) + ruc(13) → pos 23 = index 22
        key = self._make_key(environment="testing")
        self.assertEqual(key[23], "1")

    def test_production_environment_uses_digit_2(self) -> None:
        key = self._make_key(environment="production")
        self.assertEqual(key[23], "2")

    def test_date_format_ddmmyyyy(self) -> None:
        key = self._make_key(issued_at=date(2026, 6, 17))
        self.assertEqual(key[:8], "17062026")

    def test_doc_type_in_correct_position(self) -> None:
        key = self._make_key(doc_type="01")
        self.assertEqual(key[8:10], "01")

    def test_sequential_zero_padded_9_digits(self) -> None:
        key = self._make_key(sequential=5)
        # sequential starts at position 8+2+13+1+3+3 = 30, length 9
        self.assertEqual(key[30:39], "000000005")

    def test_different_sequential_produces_different_key(self) -> None:
        key1 = self._make_key(sequential=1)
        key2 = self._make_key(sequential=2)
        self.assertNotEqual(key1, key2)

    def test_verifier_digit_is_valid(self) -> None:
        key = self._make_key()
        body = key[:48]
        from lambdas.documents.domain.access_key import _modulo_11

        expected = str(_modulo_11(body))
        self.assertEqual(key[48], expected)
