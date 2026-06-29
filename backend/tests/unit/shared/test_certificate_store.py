from __future__ import annotations

import unittest

from botocore.exceptions import ClientError

from shared.certificates import store as store_module
from shared.certificates.store import CertificateStore
from shared.errors import ExternalServiceError


def _client_error(code: str, message: str = "boom") -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": message}}, "SecretsManager")


class FakeLogger:
    def __init__(self) -> None:
        self.errors: list[tuple[str, dict]] = []

    def error(self, message: str, **kwargs) -> None:
        self.errors.append((message, kwargs))


class FailingCreateClient:
    def create_secret(self, **kwargs) -> dict:
        raise _client_error("AccessDeniedException", "denied")


class FailingPutClient:
    def create_secret(self, **kwargs) -> dict:
        raise _client_error("ResourceExistsException", "exists")

    def put_secret_value(self, **kwargs) -> None:
        raise _client_error("ThrottlingException", "throttled")


class CertificateStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_log = store_module._log
        self.fake_log = FakeLogger()
        store_module._log = self.fake_log

    def tearDown(self) -> None:
        store_module._log = self.original_log

    def test_logs_create_secret_client_error_detail(self) -> None:
        store = CertificateStore(FailingCreateClient(), secret_prefix="/unit")

        with self.assertRaises(ExternalServiceError):
            store.put_certificate(
                tenant_id="tenant-1",
                certificate_b64="p12",
                password="secret-password",
            )

        self.assertEqual(self.fake_log.errors[0][0], "Secrets Manager create_secret error")
        self.assertEqual(self.fake_log.errors[0][1]["tenant_id"], "tenant-1")
        self.assertIn("AccessDeniedException", self.fake_log.errors[0][1]["error"])
        self.assertNotIn("secret-password", self.fake_log.errors[0][1]["error"])

    def test_logs_put_secret_value_client_error_detail(self) -> None:
        store = CertificateStore(FailingPutClient(), secret_prefix="/unit")

        with self.assertRaises(ExternalServiceError):
            store.put_certificate(
                tenant_id="tenant-1",
                certificate_b64="p12",
                password="secret-password",
            )

        self.assertEqual(self.fake_log.errors[0][0], "Secrets Manager put_secret_value error")
        self.assertEqual(self.fake_log.errors[0][1]["tenant_id"], "tenant-1")
        self.assertIn("ThrottlingException", self.fake_log.errors[0][1]["error"])
        self.assertNotIn("secret-password", self.fake_log.errors[0][1]["error"])


if __name__ == "__main__":
    unittest.main()
