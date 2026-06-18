from __future__ import annotations

import unittest
from typing import Any

from lambdas.sequences.domain.commands import (
    AddEmissionPointCommand,
    CreateEstablishmentCommand,
    EditEmissionPointCommand,
)
from lambdas.sequences.domain.entities import EmissionPoint, Establishment
from lambdas.sequences.domain.errors import (
    EmissionPointCode099ReservedError,
    EmissionPointCodeExistsError,
    EmissionPointNotFoundError,
    EstablishmentCodeExistsError,
    EstablishmentNotFoundError,
    SequenceAlreadyUsedError,
)
from lambdas.sequences.use_cases.add_emission_point import (
    AddEmissionPointResult,
    AddEmissionPointUseCase,
)
from lambdas.sequences.use_cases.create_establishment import CreateEstablishmentUseCase
from lambdas.sequences.use_cases.edit_emission_point import EditEmissionPointUseCase
from lambdas.sequences.use_cases.list_establishments import ListEstablishmentsUseCase
from tests.unit.support import configure_unit_environment

configure_unit_environment()


# ── Fake repo ─────────────────────────────────────────────────────────────────


class FakeSequencesRepository:
    def __init__(self) -> None:
        self.establishments: dict[str, Establishment] = {}
        self.sequences: dict[str, dict] = {}
        self.commit_calls: list[dict[str, Any]] = []
        self.bootstrap_calls: list[str] = []

    def find_establishment(self, tenant_id: str, code: str) -> Establishment | None:
        return self.establishments.get(f"{tenant_id}#{code}")

    def get_establishment(self, tenant_id: str, code: str) -> Establishment:
        e = self.find_establishment(tenant_id, code)
        if e is None:
            raise EstablishmentNotFoundError()
        return e

    def list_establishments(self, tenant_id: str) -> list[Establishment]:
        return sorted(
            [e for e in self.establishments.values() if e.tenant_id == tenant_id],
            key=lambda x: x.code,
        )

    def commit(self, *, establishment: Establishment, **kwargs: Any) -> None:
        self.commit_calls.append({"establishment": establishment, **kwargs})
        self.establishments[f"{establishment.tenant_id}#{establishment.code}"] = establishment

    def has_sequence_started(self, tenant_id: str, serie: str) -> bool:
        key = f"{tenant_id}#{serie}"
        info = self.sequences.get(key, {})
        current = info.get("current", 0)
        initial = info.get("initial", 1)
        return current > (initial - 1)

    def reserve_next(self, tenant_id: str, serie: str) -> int:
        key = f"{tenant_id}#{serie}"
        info = self.sequences.setdefault(key, {"current": 0, "initial": 1})
        info["current"] += 1
        return info["current"]

    def bootstrap_testing_point(self, tenant_id: str) -> None:
        self.bootstrap_calls.append(tenant_id)

    # Test helpers

    def seed_establishment(self, establishment: Establishment) -> None:
        self.establishments[f"{establishment.tenant_id}#{establishment.code}"] = establishment

    def seed_sequence(self, tenant_id: str, serie: str, current: int, initial: int = 1) -> None:
        self.sequences[f"{tenant_id}#{serie}"] = {"current": current, "initial": initial}


def _make_establishment(
    tenant_id: str = "t-1",
    code: str = "001",
    label: str = "Matriz",
    **kwargs: Any,
) -> Establishment:
    e = Establishment(code=code, label=label, tenant_id=tenant_id, **kwargs)
    return e


def _create_cmd(**overrides: Any) -> CreateEstablishmentCommand:
    return CreateEstablishmentCommand(
        tenant_id=overrides.get("tenant_id", "t-1"),
        code=overrides.get("code", "001"),
        label=overrides.get("label", "Matriz"),
        created_by=overrides.get("created_by", "user-1"),
    )


def _add_ep_cmd(**overrides: Any) -> AddEmissionPointCommand:
    return AddEmissionPointCommand(
        tenant_id=overrides.get("tenant_id", "t-1"),
        establishment_code=overrides.get("establishment_code", "001"),
        code=overrides.get("code", "001"),
        label=overrides.get("label", "Principal"),
        initial_sequential=overrides.get("initial_sequential", 1),
        created_by=overrides.get("created_by", "user-1"),
    )


def _edit_ep_cmd(**overrides: Any) -> EditEmissionPointCommand:
    return EditEmissionPointCommand(
        tenant_id=overrides.get("tenant_id", "t-1"),
        establishment_code=overrides.get("establishment_code", "001"),
        code=overrides.get("code", "001"),
        label=overrides.get("label"),
        initial_sequential=overrides.get("initial_sequential"),
        updated_by=overrides.get("updated_by", "user-1"),
    )


# ── CreateEstablishmentUseCase ────────────────────────────────────────────────


class CreateEstablishmentUseCaseTests(unittest.TestCase):
    def test_returns_establishment_in_memory(self) -> None:
        repo = FakeSequencesRepository()
        establishment = CreateEstablishmentUseCase(repo).execute(_create_cmd())

        self.assertEqual(establishment.code, "001")
        self.assertEqual(establishment.label, "Matriz")
        self.assertEqual(establishment.tenant_id, "t-1")
        self.assertEqual(establishment.version, 1)
        self.assertEqual(establishment.emission_points, [])
        self.assertEqual(repo.commit_calls, [])

    def test_strips_label_whitespace(self) -> None:
        repo = FakeSequencesRepository()
        establishment = CreateEstablishmentUseCase(repo).execute(
            _create_cmd(label="  Sucursal Norte  ")
        )
        self.assertEqual(establishment.label, "Sucursal Norte")

    def test_raises_if_code_already_exists(self) -> None:
        repo = FakeSequencesRepository()
        repo.seed_establishment(_make_establishment(code="001"))

        with self.assertRaises(EstablishmentCodeExistsError):
            CreateEstablishmentUseCase(repo).execute(_create_cmd(code="001"))

    def test_different_code_succeeds(self) -> None:
        repo = FakeSequencesRepository()
        repo.seed_establishment(_make_establishment(code="001"))

        establishment = CreateEstablishmentUseCase(repo).execute(_create_cmd(code="002"))
        self.assertEqual(establishment.code, "002")


# ── AddEmissionPointUseCase ───────────────────────────────────────────────────


class AddEmissionPointUseCaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = FakeSequencesRepository()
        self.repo.seed_establishment(_make_establishment())

    def test_adds_emission_point_and_increments_version(self) -> None:
        result = AddEmissionPointUseCase(self.repo).execute(_add_ep_cmd(code="001"))

        self.assertIsInstance(result, AddEmissionPointResult)
        self.assertEqual(result.establishment.version, 2)
        self.assertEqual(len(result.establishment.emission_points), 1)
        self.assertEqual(result.establishment.emission_points[0].code, "001")
        self.assertEqual(result.new_emission_point.code, "001")
        self.assertEqual(self.repo.commit_calls, [])

    def test_strips_label_whitespace(self) -> None:
        result = AddEmissionPointUseCase(self.repo).execute(_add_ep_cmd(label="  Emisor 1  "))
        self.assertEqual(result.new_emission_point.label, "Emisor 1")

    def test_raises_if_code_099_reserved(self) -> None:
        with self.assertRaises(EmissionPointCode099ReservedError):
            AddEmissionPointUseCase(self.repo).execute(_add_ep_cmd(code="099"))

    def test_raises_if_code_already_exists(self) -> None:
        ep = EmissionPoint(code="001", label="Existing")
        self.repo.establishments["t-1#001"].emission_points.append(ep)

        with self.assertRaises(EmissionPointCodeExistsError):
            AddEmissionPointUseCase(self.repo).execute(_add_ep_cmd(code="001"))

    def test_raises_if_establishment_not_found(self) -> None:
        with self.assertRaises(EstablishmentNotFoundError):
            AddEmissionPointUseCase(self.repo).execute(_add_ep_cmd(establishment_code="002"))

    def test_custom_initial_sequential(self) -> None:
        result = AddEmissionPointUseCase(self.repo).execute(
            _add_ep_cmd(code="001", initial_sequential=1000)
        )
        self.assertEqual(result.new_emission_point.initial_sequential, 1000)


# ── EditEmissionPointUseCase ──────────────────────────────────────────────────


class EditEmissionPointUseCaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo = FakeSequencesRepository()
        establishment = _make_establishment()
        establishment.emission_points = [
            EmissionPoint(code="001", label="Principal", initial_sequential=1)
        ]
        self.repo.seed_establishment(establishment)

    def test_edits_label(self) -> None:
        result = EditEmissionPointUseCase(self.repo).execute(
            _edit_ep_cmd(code="001", label="Nuevo Nombre")
        )

        ep = result.establishment.find_emission_point("001")
        self.assertEqual(ep.label, "Nuevo Nombre")
        self.assertEqual(ep.initial_sequential, 1)
        self.assertEqual(result.establishment.version, 2)
        self.assertIsNone(result.update_sequence)

    def test_edits_initial_sequential_when_not_started(self) -> None:
        result = EditEmissionPointUseCase(self.repo).execute(
            _edit_ep_cmd(code="001", initial_sequential=500)
        )

        ep = result.establishment.find_emission_point("001")
        self.assertEqual(ep.initial_sequential, 500)
        self.assertEqual(result.update_sequence, ("001001", 500))

    def test_no_sequence_update_when_initial_unchanged(self) -> None:
        result = EditEmissionPointUseCase(self.repo).execute(
            _edit_ep_cmd(code="001", initial_sequential=1)
        )
        self.assertIsNone(result.update_sequence)

    def test_raises_if_sequence_started(self) -> None:
        self.repo.seed_sequence("t-1", "001001", current=1, initial=1)

        with self.assertRaises(SequenceAlreadyUsedError):
            EditEmissionPointUseCase(self.repo).execute(
                _edit_ep_cmd(code="001", initial_sequential=100)
            )

    def test_raises_if_emission_point_not_found(self) -> None:
        with self.assertRaises(EmissionPointNotFoundError):
            EditEmissionPointUseCase(self.repo).execute(_edit_ep_cmd(code="099"))

    def test_raises_if_establishment_not_found(self) -> None:
        with self.assertRaises(EstablishmentNotFoundError):
            EditEmissionPointUseCase(self.repo).execute(
                _edit_ep_cmd(establishment_code="999", code="001")
            )

    def test_none_fields_not_applied(self) -> None:
        result = EditEmissionPointUseCase(self.repo).execute(
            _edit_ep_cmd(code="001", label=None, initial_sequential=None)
        )
        ep = result.establishment.find_emission_point("001")
        self.assertEqual(ep.label, "Principal")
        self.assertEqual(ep.initial_sequential, 1)


# ── ListEstablishmentsUseCase ─────────────────────────────────────────────────


class ListEstablishmentsUseCaseTests(unittest.TestCase):
    def test_returns_empty_list_when_no_establishments(self) -> None:
        repo = FakeSequencesRepository()
        result = ListEstablishmentsUseCase(repo).execute("t-1")
        self.assertEqual(result, [])

    def test_returns_establishments_sorted_by_code(self) -> None:
        repo = FakeSequencesRepository()
        repo.seed_establishment(_make_establishment(code="003"))
        repo.seed_establishment(_make_establishment(code="001"))
        repo.seed_establishment(_make_establishment(code="002"))

        result = ListEstablishmentsUseCase(repo).execute("t-1")
        self.assertEqual([e.code for e in result], ["001", "002", "003"])

    def test_filters_by_tenant(self) -> None:
        repo = FakeSequencesRepository()
        repo.seed_establishment(_make_establishment(tenant_id="t-1", code="001"))
        repo.seed_establishment(_make_establishment(tenant_id="t-2", code="001"))

        result = ListEstablishmentsUseCase(repo).execute("t-1")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].tenant_id, "t-1")
