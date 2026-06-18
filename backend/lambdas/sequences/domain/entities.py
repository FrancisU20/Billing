from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass
class EmissionPoint:
    code: str
    label: str
    initial_sequential: int = 1

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "label": self.label,
            "initial_sequential": self.initial_sequential,
        }

    @classmethod
    def from_dict(cls, d: dict) -> EmissionPoint:
        return cls(
            code=d["code"],
            label=d["label"],
            initial_sequential=d.get("initial_sequential", 1),
        )


@dataclass
class Establishment:
    code: str
    label: str
    tenant_id: str
    emission_points: list[EmissionPoint] = field(default_factory=list)
    version: int = 1
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    created_by: str = ""
    updated_by: str = ""

    def find_emission_point(self, code: str) -> EmissionPoint | None:
        for ep in self.emission_points:
            if ep.code == code:
                return ep
        return None

    def has_emission_point(self, code: str) -> bool:
        return self.find_emission_point(code) is not None

    def add_emission_point(self, ep: EmissionPoint, added_by: str) -> None:
        self.emission_points.append(ep)
        self.updated_at = _now()
        self.updated_by = added_by
        self.version += 1

    def edit_emission_point(
        self,
        code: str,
        label: str | None,
        initial_sequential: int | None,
        updated_by: str,
    ) -> None:
        ep = self.find_emission_point(code)
        if ep is None:
            from lambdas.sequences.domain.errors import EmissionPointNotFoundError

            raise EmissionPointNotFoundError()
        if label is not None:
            ep.label = label
        if initial_sequential is not None:
            ep.initial_sequential = initial_sequential
        self.updated_at = _now()
        self.updated_by = updated_by
        self.version += 1

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "label": self.label,
            "tenant_id": self.tenant_id,
            "emission_points": [ep.to_dict() for ep in self.emission_points],
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
            "updated_by": self.updated_by,
        }
