from __future__ import annotations

import importlib
import os
import sys
import unittest
from unittest.mock import patch

from lambdas.sequences.domain.entities import EmissionPoint
from tests.unit.lambdas.sequences.test_use_cases import (
    FakeSequencesRepository,
    _make_establishment,
)
from tests.unit.support import LambdaContext, api_event, configure_unit_environment, decode_response

_CTX = LambdaContext()
_FAKE_IDEMPOTENCY = object()


def _load_handler():
    configure_unit_environment()
    os.environ["SEQUENCES_TABLE"] = "unit-sequences"
    os.environ.pop("IDEMPOTENCY_TABLE", None)
    sys.modules.pop("lambdas.sequences.handler", None)
    sys.modules.pop("lambdas._base.idempotency", None)
    return importlib.import_module("lambdas.sequences.handler")


def _event(method, path, **kwargs):
    return api_event(method=method, path=path, **kwargs)


# ── GET /tenants/{id}/establishments ─────────────────────────────────────────


class ListEstablishmentsHandlerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mod = _load_handler()

    def test_returns_empty_list(self) -> None:
        repo = FakeSequencesRepository()
        with patch.object(self.mod, "_repo", return_value=repo):
            resp = self.mod.handler(_event("GET", "/tenants/t-1/establishments"), _CTX)
        body = decode_response(resp)
        self.assertEqual(resp["statusCode"], 200)
        self.assertEqual(body["data"]["items"], [])

    def test_returns_establishments(self) -> None:
        repo = FakeSequencesRepository()
        repo.seed_establishment(_make_establishment(tenant_id="t-1", code="001"))
        with patch.object(self.mod, "_repo", return_value=repo):
            resp = self.mod.handler(_event("GET", "/tenants/t-1/establishments"), _CTX)
        body = decode_response(resp)
        self.assertEqual(resp["statusCode"], 200)
        self.assertEqual(len(body["data"]["items"]), 1)
        self.assertEqual(body["data"]["items"][0]["code"], "001")

    def test_forbidden_if_wrong_tenant(self) -> None:
        repo = FakeSequencesRepository()
        with patch.object(self.mod, "_repo", return_value=repo):
            resp = self.mod.handler(
                _event(
                    "GET",
                    "/tenants/t-99/establishments",
                    claims={
                        "custom:tenant_id": "t-1",
                        "custom:role": "owner",
                        "custom:is_superadmin": "false",
                    },
                ),
                _CTX,
            )
        self.assertEqual(resp["statusCode"], 403)

    def test_superadmin_can_access_any_tenant(self) -> None:
        repo = FakeSequencesRepository()
        repo.seed_establishment(_make_establishment(tenant_id="t-99", code="001"))
        with patch.object(self.mod, "_repo", return_value=repo):
            resp = self.mod.handler(_event("GET", "/tenants/t-99/establishments"), _CTX)
        self.assertEqual(resp["statusCode"], 200)


# ── POST /tenants/{id}/establishments ────────────────────────────────────────


class CreateEstablishmentHandlerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mod = _load_handler()

    def _call(self, repo: FakeSequencesRepository, body: dict, headers=None) -> dict:
        with (
            patch.object(self.mod, "_repo", return_value=repo),
            patch.object(self.mod, "require_current_context", return_value=_FAKE_IDEMPOTENCY),
        ):
            return self.mod.handler(
                _event(
                    "POST",
                    "/tenants/t-1/establishments",
                    body=body,
                    headers=headers if headers is not None else {"x-idempotency-key": "key-1"},
                ),
                _CTX,
            )

    def test_creates_establishment(self) -> None:
        repo = FakeSequencesRepository()
        resp = self._call(repo, {"code": "001", "label": "Matriz"})
        body = decode_response(resp)
        self.assertEqual(resp["statusCode"], 201)
        self.assertEqual(body["data"]["code"], "001")
        self.assertEqual(body["data"]["label"], "Matriz")
        self.assertEqual(body["data"]["emission_points"], [])
        self.assertEqual(len(repo.commit_calls), 1)
        self.assertEqual(repo.commit_calls[0]["action"], "CREATE")
        self.assertIs(repo.commit_calls[0]["idempotency"], _FAKE_IDEMPOTENCY)

    def test_returns_409_if_code_exists(self) -> None:
        repo = FakeSequencesRepository()
        repo.seed_establishment(_make_establishment(code="001"))
        resp = self._call(repo, {"code": "001", "label": "Otra"})
        self.assertEqual(resp["statusCode"], 409)

    def test_rejects_non_digit_code(self) -> None:
        repo = FakeSequencesRepository()
        resp = self._call(repo, {"code": "AB1", "label": "Bad"})
        self.assertEqual(resp["statusCode"], 400)

    def test_rejects_code_too_short(self) -> None:
        repo = FakeSequencesRepository()
        resp = self._call(repo, {"code": "01", "label": "Short"})
        self.assertEqual(resp["statusCode"], 400)


# ── POST /tenants/{id}/establishments/{code}/emission-points ─────────────────


class AddEmissionPointHandlerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mod = _load_handler()
        self.repo = FakeSequencesRepository()
        self.repo.seed_establishment(_make_establishment(tenant_id="t-1", code="001"))

    def _call(self, body: dict) -> dict:
        with (
            patch.object(self.mod, "_repo", return_value=self.repo),
            patch.object(self.mod, "require_current_context", return_value=_FAKE_IDEMPOTENCY),
        ):
            return self.mod.handler(
                _event(
                    "POST",
                    "/tenants/t-1/establishments/001/emission-points",
                    body=body,
                    headers={"x-idempotency-key": "key-2"},
                    path_params={"id": "t-1", "code": "001"},
                ),
                _CTX,
            )

    def test_adds_emission_point(self) -> None:
        resp = self._call({"code": "001", "label": "Principal"})
        body = decode_response(resp)
        self.assertEqual(resp["statusCode"], 201)
        eps = body["data"]["emission_points"]
        self.assertEqual(len(eps), 1)
        self.assertEqual(eps[0]["code"], "001")
        self.assertEqual(eps[0]["initial_sequential"], 1)
        call = self.repo.commit_calls[0]
        self.assertIsNotNone(call["new_emission_point"])

    def test_rejects_code_099(self) -> None:
        resp = self._call({"code": "099", "label": "Pruebas"})
        self.assertEqual(resp["statusCode"], 422)

    def test_returns_404_if_establishment_not_found(self) -> None:
        self.repo.establishments.clear()
        resp = self._call({"code": "001", "label": "x"})
        self.assertEqual(resp["statusCode"], 404)

    def test_custom_initial_sequential(self) -> None:
        resp = self._call({"code": "001", "label": "p", "initial_sequential": 500})
        body = decode_response(resp)
        self.assertEqual(resp["statusCode"], 201)
        self.assertEqual(body["data"]["emission_points"][0]["initial_sequential"], 500)


# ── PATCH /tenants/{id}/establishments/{code}/emission-points/{point} ────────


class EditEmissionPointHandlerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mod = _load_handler()
        self.repo = FakeSequencesRepository()
        estab = _make_establishment(tenant_id="t-1", code="001")
        estab.emission_points = [EmissionPoint(code="001", label="Original", initial_sequential=1)]
        self.repo.seed_establishment(estab)

    def _call(self, body: dict, point: str = "001") -> dict:
        with (
            patch.object(self.mod, "_repo", return_value=self.repo),
            patch.object(self.mod, "require_current_context", return_value=_FAKE_IDEMPOTENCY),
        ):
            return self.mod.handler(
                _event(
                    "PATCH",
                    f"/tenants/t-1/establishments/001/emission-points/{point}",
                    body=body,
                    headers={"x-idempotency-key": "key-3"},
                    path_params={"id": "t-1", "code": "001", "point": point},
                ),
                _CTX,
            )

    def test_edits_label(self) -> None:
        resp = self._call({"label": "Actualizado"})
        body = decode_response(resp)
        self.assertEqual(resp["statusCode"], 200)
        self.assertEqual(body["data"]["emission_points"][0]["label"], "Actualizado")

    def test_edits_initial_sequential(self) -> None:
        resp = self._call({"initial_sequential": 500})
        body = decode_response(resp)
        self.assertEqual(resp["statusCode"], 200)
        self.assertEqual(body["data"]["emission_points"][0]["initial_sequential"], 500)
        call = self.repo.commit_calls[0]
        self.assertEqual(call["update_sequence"], ("001001", 500))

    def test_returns_404_if_emission_point_not_found(self) -> None:
        resp = self._call({"label": "x"}, point="099")
        self.assertEqual(resp["statusCode"], 404)

    def test_returns_409_if_sequence_started(self) -> None:
        self.repo.seed_sequence("t-1", "001001", current=1, initial=1)
        resp = self._call({"initial_sequential": 100})
        self.assertEqual(resp["statusCode"], 409)


# ── Unknown route ─────────────────────────────────────────────────────────────


class UnknownRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mod = _load_handler()

    def test_unknown_method_returns_404(self) -> None:
        repo = FakeSequencesRepository()
        with patch.object(self.mod, "_repo", return_value=repo):
            resp = self.mod.handler(_event("DELETE", "/tenants/t-1/establishments"), _CTX)
        self.assertEqual(resp["statusCode"], 404)
