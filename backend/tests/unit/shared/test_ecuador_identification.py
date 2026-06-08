from __future__ import annotations

import unittest

from shared.domain.value_objects.ruc import RUC
from shared.errors import ValidationError


class EcuadorIdentificationTests(unittest.TestCase):
    def test_ruc_requires_complete_13_digits(self) -> None:
        with self.assertRaises(ValidationError):
            RUC("1710034065")

    def test_natural_person_ruc_uses_valid_cedula_and_001_suffix(self) -> None:
        self.assertEqual(str(RUC("1710034065001")), "1710034065001")

        with self.assertRaises(ValidationError):
            RUC("1710034065002")

    def test_legal_entity_ruc_remains_valid(self) -> None:
        self.assertEqual(str(RUC("1792146739001")), "1792146739001")

    def test_rejects_invalid_province(self) -> None:
        with self.assertRaises(ValidationError):
            RUC("2592146739001")


if __name__ == "__main__":
    unittest.main()
