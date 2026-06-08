from __future__ import annotations

from dataclasses import dataclass, field
import re

from lambdas.clients.domain.commands import CreateClientCommand, UpdateClientCommand
from lambdas.clients.domain.enums import ClientStatus, IdentificationType, PersonType
from lambdas.clients.domain.value_objects.address import Address
from lambdas.clients.domain.value_objects.cedula import Cedula
from shared.domain.base_entity import TenantScopedEntity
from shared.domain.value_objects.email import Email
from shared.domain.value_objects.ruc import RUC
from shared.errors import ValidationError

_FREE_IDENTIFICATION_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._\-/]{2,24}$")


@dataclass
class Client(TenantScopedEntity):
    identification: str = ""
    identification_type: IdentificationType = IdentificationType.RUC
    person_type: PersonType = PersonType.NATURAL
    legal_name: str = ""
    trade_name: str = ""
    special_taxpayer: bool = False
    emails: list[str] = field(default_factory=list)
    phones: list[str] = field(default_factory=list)
    addresses: list[Address] = field(default_factory=list)
    status: ClientStatus = ClientStatus.ACTIVE

    @classmethod
    def create(cls, cmd: CreateClientCommand) -> Client:
        identification_type = _identification_type(cmd.identification_type)
        person_type = _person_type(cmd.person_type)
        identification = _normalize_identification(cmd.identification, identification_type)
        _validate_person_type(identification_type, person_type)
        return cls(
            tenant_id=cmd.tenant_id,
            identification=identification,
            identification_type=identification_type,
            person_type=person_type,
            legal_name=_required_text(cmd.legal_name, "legal_name"),
            trade_name=_optional_text(cmd.trade_name),
            special_taxpayer=bool(cmd.special_taxpayer),
            emails=_normalize_emails(cmd.emails or []),
            phones=_normalize_phones(cmd.phones or []),
            addresses=_normalize_addresses(cmd.addresses or []),
            status=ClientStatus.ACTIVE,
            created_by=cmd.created_by,
            updated_by=cmd.created_by,
        )

    def update(self, cmd: UpdateClientCommand) -> None:
        next_identification_type = (
            _identification_type(cmd.identification_type)
            if cmd.identification_type is not None
            else self.identification_type
        )
        next_person_type = (
            _person_type(cmd.person_type) if cmd.person_type is not None else self.person_type
        )
        next_identification = (
            _normalize_identification(cmd.identification, next_identification_type)
            if cmd.identification is not None
            else _normalize_identification(self.identification, next_identification_type)
        )
        _validate_person_type(next_identification_type, next_person_type)

        self.identification_type = next_identification_type
        self.person_type = next_person_type
        self.identification = next_identification
        if cmd.legal_name is not None:
            self.legal_name = _required_text(cmd.legal_name, "legal_name")
        if cmd.trade_name is not None:
            self.trade_name = _optional_text(cmd.trade_name)
        if cmd.special_taxpayer is not None:
            self.special_taxpayer = bool(cmd.special_taxpayer)
        if cmd.emails is not None:
            self.emails = _normalize_emails(cmd.emails)
        if cmd.phones is not None:
            self.phones = _normalize_phones(cmd.phones)
        if cmd.addresses is not None:
            self.addresses = _normalize_addresses(cmd.addresses)
        if cmd.status is not None:
            try:
                self.status = ClientStatus(cmd.status)
            except ValueError as exc:
                raise ValidationError("Estado de cliente inválido") from exc
        self.touch(cmd.updated_by)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "identification": self.identification,
            "identification_type": self.identification_type.value,
            "person_type": self.person_type.value,
            "legal_name": self.legal_name,
            "trade_name": self.trade_name,
            "special_taxpayer": self.special_taxpayer,
            "emails": self.emails,
            "phones": self.phones,
            "addresses": [a.to_dict() for a in self.addresses],
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "created_by": self.created_by,
            "updated_by": self.updated_by,
            "version": self.version,
        }


def _identification_type(value: str) -> IdentificationType:
    try:
        return IdentificationType(value)
    except ValueError as exc:
        raise ValidationError("Tipo de identificación inválido") from exc


def _person_type(value: str) -> PersonType:
    try:
        return PersonType(value)
    except ValueError as exc:
        raise ValidationError("Tipo de persona inválido") from exc


def _normalize_identification(value: str, identification_type: IdentificationType) -> str:
    value = (value or "").strip().upper()
    if identification_type == IdentificationType.RUC:
        if len(value) != 13:
            raise ValidationError("RUC inválido")
        return str(RUC(value))
    if identification_type == IdentificationType.CEDULA:
        return str(Cedula(value))
    if not _FREE_IDENTIFICATION_RE.match(value):
        raise ValidationError("Identificación inválida")
    return value


def _validate_person_type(
    identification_type: IdentificationType,
    person_type: PersonType,
) -> None:
    if identification_type == IdentificationType.CEDULA and person_type != PersonType.NATURAL:
        raise ValidationError("La cédula solo aplica para persona natural")


def _required_text(value: str, field_name: str) -> str:
    value = (value or "").strip()
    if not value:
        raise ValidationError(f"{field_name} es requerido")
    return value


def _optional_text(value: str) -> str:
    return (value or "").strip()


def _normalize_emails(values: list[str]) -> list[str]:
    return [str(Email(v)) for v in values if (v or "").strip()]


def _normalize_phones(values: list[str]) -> list[str]:
    return [(v or "").strip() for v in values if (v or "").strip()]


def _normalize_addresses(values) -> list[Address]:
    addresses: list[Address] = []
    for value in values:
        if isinstance(value, Address):
            addresses.append(value)
        elif isinstance(value, dict):
            addresses.append(Address.from_dict(value))
        else:
            addresses.append(Address(label=value.label, line=value.line, city=value.city))
    return addresses
