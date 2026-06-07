from __future__ import annotations

"""Value Object: email address normalized to lowercase."""
import re

from shared.errors import ValidationError

_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")


class Email:
    def __init__(self, value: str) -> None:
        value = (value or "").strip().lower()
        if not _RE.match(value):
            raise ValidationError("Email inválido")
        self.value = value

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"Email({self.value!r})"

    def __eq__(self, other) -> bool:
        return self.value == (other.value if isinstance(other, Email) else str(other).lower())

    def __hash__(self) -> int:
        return hash(self.value)
