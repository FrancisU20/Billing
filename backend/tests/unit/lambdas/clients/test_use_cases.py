from __future__ import annotations

import unittest

from lambdas.clients.domain.commands import UpdateClientCommand
from lambdas.clients.domain.enums import ClientStatus
from lambdas.clients.use_cases.create_client import CreateClientUseCase
from lambdas.clients.use_cases.delete_client import DeleteClientUseCase
from lambdas.clients.use_cases.list_clients import ListClientsQuery, ListClientsUseCase
from lambdas.clients.use_cases.update_client import UpdateClientUseCase
from shared.errors import ValidationError
from tests.unit.support import (
    FakeClientRepository,
    create_client_command,
    make_client,
)


class CreateClientUseCaseTests(unittest.TestCase):
    def test_create_returns_client_without_persisting(self) -> None:
        repo = FakeClientRepository()
        client = CreateClientUseCase(repo).execute(create_client_command())

        self.assertEqual(client.tenant_id, "tenant-1")
        self.assertEqual(client.identification, "1792146739001")
        self.assertEqual(client.emails, ["cliente@codelabs.com"])
        self.assertEqual(repo.commit_calls, [])
        self.assertEqual(repo.get_by_identification_calls, [])

    def test_create_rejects_invalid_ruc(self) -> None:
        with self.assertRaises(ValidationError):
            CreateClientUseCase(FakeClientRepository()).execute(
                create_client_command(identification="179214673900")
            )

    def test_create_accepts_pasaporte_without_foreign_field(self) -> None:
        client = CreateClientUseCase(FakeClientRepository()).execute(
            create_client_command(
                identification="A12345678",
                identification_type="pasaporte",
                person_type="natural",
            )
        )

        self.assertEqual(client.identification_type.value, "pasaporte")
        self.assertNotIn("foreign", client.to_dict())

    def test_create_accepts_exterior_without_foreign_field(self) -> None:
        client = CreateClientUseCase(FakeClientRepository()).execute(
            create_client_command(
                identification="TAX-998877",
                identification_type="exterior",
                person_type="juridica",
            )
        )

        self.assertEqual(client.identification_type.value, "exterior")
        self.assertNotIn("foreign", client.to_dict())

    def test_to_dict_does_not_expose_foreign(self) -> None:
        client = CreateClientUseCase(FakeClientRepository()).execute(create_client_command())

        self.assertNotIn("foreign", client.to_dict())

    def test_create_does_not_precheck_duplicate_identification(self) -> None:
        repo = FakeClientRepository()
        repo.existing_by_identification = make_client(id="client-existing")

        client = CreateClientUseCase(repo).execute(create_client_command())

        self.assertEqual(client.identification, "1792146739001")
        self.assertEqual(repo.get_by_identification_calls, [])


class ClientMutationUseCaseTests(unittest.TestCase):
    def test_update_changes_identification_and_excludes_own_id(self) -> None:
        repo = FakeClientRepository()
        client = make_client(id="client-1")
        repo.clients[client.id] = client

        updated = UpdateClientUseCase(repo).execute(
            UpdateClientCommand(
                client_id="client-1",
                updated_by="admin-1",
                identification="1710034065",
                identification_type="cedula",
                person_type="natural",
                legal_name="Persona Natural",
            )
        )

        self.assertEqual(updated.identification, "1710034065")
        self.assertEqual(updated.identification_type.value, "cedula")
        self.assertEqual(updated.person_type.value, "natural")
        self.assertEqual(repo.get_by_identification_calls, [])

    def test_update_does_not_precheck_duplicate_identification(self) -> None:
        repo = FakeClientRepository()
        client = make_client(id="client-1")
        repo.clients[client.id] = client
        repo.existing_by_identification = make_client(id="client-2")

        updated = UpdateClientUseCase(repo).execute(
            UpdateClientCommand(
                client_id="client-1",
                updated_by="admin-1",
                trade_name="Nueva marca",
            )
        )

        self.assertEqual(updated.trade_name, "Nueva marca")
        self.assertEqual(repo.get_by_identification_calls, [])

    def test_update_rejects_juridica_with_cedula(self) -> None:
        repo = FakeClientRepository()
        client = make_client(id="client-1")
        repo.clients[client.id] = client

        with self.assertRaises(ValidationError):
            UpdateClientUseCase(repo).execute(
                UpdateClientCommand(
                    client_id="client-1",
                    updated_by="admin-1",
                    identification="1710034065",
                    identification_type="cedula",
                    person_type="juridica",
                )
            )

    def test_delete_soft_deletes(self) -> None:
        repo = FakeClientRepository()
        client = make_client(id="client-1")
        repo.clients[client.id] = client

        deleted = DeleteClientUseCase(repo).execute("client-1", "admin-1")

        self.assertTrue(deleted.deleted)
        self.assertEqual(deleted.deleted_by, "admin-1")

    def test_list_delegates_to_repository(self) -> None:
        repo = FakeClientRepository()
        expected = make_client(id="client-1")
        repo.list_result = ([expected], "cursor-1")

        clients, next_token = ListClientsUseCase(repo).execute(
            ListClientsQuery(
                limit=10,
                next_token="cursor-0",
                status=ClientStatus.ACTIVE.value,
                identification="1792146739001",
                identification_type="ruc",
                created_from="2026-06-01T00:00:00+00:00",
                created_to="2026-06-08T23:59:59.999999+00:00",
            )
        )

        self.assertEqual(clients, [expected])
        self.assertEqual(next_token, "cursor-1")
        self.assertEqual(repo.list_calls[0]["identification"], "1792146739001")
        self.assertEqual(repo.list_calls[0]["identification_type"], "ruc")
        self.assertEqual(repo.list_calls[0]["created_from"], "2026-06-01T00:00:00+00:00")
        self.assertEqual(repo.list_calls[0]["created_to"], "2026-06-08T23:59:59.999999+00:00")

    def test_count_delegates_to_repository_without_text_filters(self) -> None:
        repo = FakeClientRepository()
        repo.count_result = 42

        total = ListClientsUseCase(repo).count(
            ListClientsQuery(limit=10, status=ClientStatus.ACTIVE.value)
        )

        self.assertEqual(total, 42)
        self.assertEqual(repo.count_calls[0]["status"], ClientStatus.ACTIVE.value)

    def test_count_is_none_when_q_filter_is_active(self) -> None:
        repo = FakeClientRepository()
        repo.count_result = 42

        total = ListClientsUseCase(repo).count(ListClientsQuery(limit=10, q="acme"))

        self.assertIsNone(total)
        self.assertEqual(repo.count_calls, [])

    def test_count_is_none_when_identification_filter_is_active(self) -> None:
        repo = FakeClientRepository()
        repo.count_result = 42

        total = ListClientsUseCase(repo).count(
            ListClientsQuery(limit=10, identification="1792146739001")
        )

        self.assertIsNone(total)
        self.assertEqual(repo.count_calls, [])


if __name__ == "__main__":
    unittest.main()
