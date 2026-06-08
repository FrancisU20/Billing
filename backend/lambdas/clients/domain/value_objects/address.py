from __future__ import annotations

from dataclasses import dataclass

from shared.errors import ValidationError


@dataclass(frozen=True)
class Address:
    label: str
    line: str
    city: str = ""

    def __post_init__(self) -> None:
        label = (self.label or "").strip()
        line = (self.line or "").strip()
        city = (self.city or "").strip()
        if not label:
            raise ValidationError("La etiqueta de la dirección es requerida")
        if not line:
            raise ValidationError("La dirección es requerida")
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "line", line)
        object.__setattr__(self, "city", city)

    @classmethod
    def from_dict(cls, data: dict) -> Address:
        return cls(
            label=data.get("label", ""),
            line=data.get("line", ""),
            city=data.get("city", ""),
        )

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "line": self.line,
            "city": self.city,
        }
