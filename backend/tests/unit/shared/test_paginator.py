from __future__ import annotations

import base64
import json
import unittest

from shared.db.paginator import decode_cursor, encode_cursor
from shared.errors import ValidationError


class EncodeCursorTests(unittest.TestCase):
    def test_none_returns_none(self) -> None:
        self.assertIsNone(encode_cursor(None))

    def test_empty_dict_returns_none(self) -> None:
        self.assertIsNone(encode_cursor({}))

    def test_encodes_to_base64_json(self) -> None:
        key = {"pk": "T#1", "sk": "CLIENT#abc"}
        result = encode_cursor(key)
        decoded = json.loads(base64.b64decode(result.encode()).decode())
        self.assertEqual(decoded, key)

    def test_result_is_string(self) -> None:
        result = encode_cursor({"pk": "T#1"})
        self.assertIsInstance(result, str)


class DecodeCursorTests(unittest.TestCase):
    def test_none_returns_none(self) -> None:
        self.assertIsNone(decode_cursor(None))

    def test_empty_string_returns_none(self) -> None:
        self.assertIsNone(decode_cursor(""))

    def test_roundtrip(self) -> None:
        key = {"pk": "T#1", "sk": "CLIENT#abc"}
        token = encode_cursor(key)
        self.assertEqual(decode_cursor(token), key)

    def test_invalid_token_raises_validation_error(self) -> None:
        with self.assertRaises(ValidationError):
            decode_cursor("not-valid-base64!!")

    def test_non_json_base64_raises_validation_error(self) -> None:
        bad = base64.b64encode(b"not json").decode()
        with self.assertRaises(ValidationError):
            decode_cursor(bad)


if __name__ == "__main__":
    unittest.main()
