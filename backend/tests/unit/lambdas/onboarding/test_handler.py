from __future__ import annotations

import importlib
import os
import sys
import unittest
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import patch

from lambdas.onboarding.domain.errors import PlanNotActiveError, PlanNotFoundError
from lambdas.onboarding.domain.repositories.i_plan_catalog import IPlanCatalog, PlanSummary
from shared.certificates.metadata import CertificateMetadata
from tests.unit.support import (
    LambdaContext,
    api_event,
    configure_unit_environment,
    decode_response,
    tenant_payload,
)


class FakeOnboardingPlanCatalog(IPlanCatalog):
    def __init__(
        self,
        *,
        exists: bool = True,
        active: bool = True,
        self_service: bool = True,
        limit_cycle: str = "month",
        is_free: bool = True,
    ) -> None:
        self.exists = exists
        self.active = active
        self.self_service = self_service
        self.limit_cycle = limit_cycle
        self.is_free = is_free
        self.checked_ids: list[str] = []

    def get(self, plan_id: str) -> PlanSummary:
        self.checked_ids.append(plan_id)
        if not self.exists:
            raise PlanNotFoundError()
        if not self.active:
            raise PlanNotActiveError()
        return PlanSummary(
            id=plan_id,
            self_service=self.self_service,
            limit_cycle=self.limit_cycle,
            is_free=self.is_free,
        )


class FakeEnterpriseLeadRepository:
    def __init__(self) -> None:
        self.commit_calls: list[dict[str, Any]] = []

    def commit(self, **kwargs: Any) -> None:
        self.commit_calls.append(kwargs)


class FakeVerificationRepository:
    def __init__(self, verification=None) -> None:
        self.verification = verification
        self.commit_request_calls: list[dict[str, Any]] = []
        self.save_attempts_calls: list[Any] = []
        self.mark_used_calls: list[Any] = []
        self.mark_used_transact_item_calls: list[Any] = []

    def get_by_id(self, verification_id: str):
        return self.verification

    def commit_request(self, **kwargs: Any) -> None:
        self.commit_request_calls.append(kwargs)

    def save_attempts(self, verification) -> None:
        self.save_attempts_calls.append(verification)

    def mark_used(self, verification) -> None:
        self.mark_used_calls.append(verification)

    def mark_used_transact_item(self, verification):
        self.mark_used_transact_item_calls.append(verification)
        return {
            "Update": {
                "TableName": "unit-tenants",
                "Key": {"id": verification.id},
                "UpdateExpression": "SET used_at = :used_at",
            }
        }


class FakeCertificateValidator:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def validate_base64(self, **kwargs: Any) -> CertificateMetadata:
        self.calls.append(kwargs)
        return CertificateMetadata(
            subject_ruc=kwargs["expected_ruc"],
            expires_at=datetime.now(UTC) + timedelta(days=365),
            issuer="Security Data",
        )


class FakeCertificateStore:
    def __init__(self) -> None:
        self.put_calls: list[dict[str, Any]] = []
        self.delete_calls: list[str] = []

    def put_certificate(self, **kwargs: Any) -> str:
        self.put_calls.append(kwargs)
        return "arn:aws:secretsmanager:sa-east-1:123:secret:/tenant/certificate"

    def delete_certificate(self, *, tenant_id: str) -> None:
        self.delete_calls.append(tenant_id)


def _load_handler_module():
    configure_unit_environment()
    os.environ["TENANTS_TABLE"] = "unit-tenants"
    os.environ["PLANS_TABLE"] = "unit-plans"
    os.environ["AUDIT_LOG_TABLE"] = "unit-audit"
    os.environ["OUTBOX_TABLE"] = ""
    os.environ.pop("IDEMPOTENCY_TABLE", None)

    sys.modules.pop("lambdas.onboarding.handler", None)
    sys.modules.pop("lambdas._base.idempotency", None)
    return importlib.import_module("lambdas.onboarding.handler")


def _request_event(**overrides: Any) -> dict:
    body = tenant_payload(certificate_b64="base64-p12", cert_password="secret", **overrides)
    return api_event(
        method="POST",
        path="/onboarding/otp/request",
        body=body,
        headers={"X-Idempotency-Key": "onboarding-request-1"},
        claims={
            "sub": "",
            "custom:tenant_id": "",
            "custom:role": "viewer",
            "custom:is_superadmin": "false",
        },
    )


def _confirm_event(**overrides: Any) -> dict:
    body = tenant_payload(
        verification_id="verification-1",
        otp="123456",
        certificate_b64="base64-p12",
        cert_password="secret",
        **overrides,
    )
    return api_event(
        method="POST",
        path="/onboarding/otp/confirm",
        body=body,
        headers={"X-Idempotency-Key": "onboarding-confirm-1"},
        claims={
            "sub": "",
            "custom:tenant_id": "",
            "custom:role": "viewer",
            "custom:is_superadmin": "false",
        },
    )


def _verification_for_confirm():
    from lambdas.onboarding.domain.commands import ConfirmOnboardingOtpCommand
    from lambdas.onboarding.domain.onboarding_verification import OnboardingVerification
    from lambdas.onboarding.use_cases.payload_signature import onboarding_payload_hash

    payload = tenant_payload()
    command = ConfirmOnboardingOtpCommand(
        verification_id="verification-1",
        otp="123456",
        certificate_b64="base64-p12",
        cert_password="secret",
        **payload,
    )
    verification = OnboardingVerification.create(
        ruc=payload["ruc"],
        email=payload["email"],
        plan_id=payload["plan_id"],
        payload_hash=onboarding_payload_hash(command),
        self_service=True,
        otp="123456",
    )
    verification.id = "verification-1"
    return verification


class OnboardingHandlerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.handler = _load_handler_module()
        self.context = LambdaContext()

    def test_request_otp_self_service_persists_verification(self) -> None:
        from tests.unit.support import FakeTenantRepository

        tenant_repo = FakeTenantRepository()
        verification_repo = FakeVerificationRepository()
        validator = FakeCertificateValidator()
        idempotency_context = object()

        with (
            patch.object(self.handler, "_tenant_repo", return_value=tenant_repo),
            patch.object(self.handler, "_verification_repo", return_value=verification_repo),
            patch.object(
                self.handler,
                "_plan_catalog",
                return_value=FakeOnboardingPlanCatalog(self_service=True),
            ),
            patch.object(self.handler, "_certificate_validator", return_value=validator),
            patch.object(self.handler, "require_current_context", return_value=idempotency_context),
        ):
            response = self.handler.handler(_request_event(), self.context)

        body = decode_response(response)
        self.assertEqual(response["statusCode"], 201)
        self.assertTrue(body["success"])
        self.assertIn("verification_id", body["data"])
        self.assertEqual(len(validator.calls), 1)
        self.assertEqual(len(verification_repo.commit_request_calls), 1)
        self.assertEqual(
            verification_repo.commit_request_calls[0]["events"][0].event_type,
            "OnboardingOtpRequestedEvent",
        )

    def test_confirm_otp_self_service_creates_tenant(self) -> None:
        from tests.unit.support import FakeTenantRepository

        tenant_repo = FakeTenantRepository()
        verification_repo = FakeVerificationRepository(_verification_for_confirm())
        validator = FakeCertificateValidator()
        store = FakeCertificateStore()
        idempotency_context = object()

        with (
            patch.object(self.handler, "_tenant_repo", return_value=tenant_repo),
            patch.object(self.handler, "_verification_repo", return_value=verification_repo),
            patch.object(
                self.handler,
                "_plan_catalog",
                return_value=FakeOnboardingPlanCatalog(self_service=True),
            ),
            patch.object(self.handler, "_certificate_validator", return_value=validator),
            patch.object(self.handler, "_certificate_store", return_value=store),
            patch.object(self.handler, "require_current_context", return_value=idempotency_context),
        ):
            response = self.handler.handler(_confirm_event(), self.context)

        body = decode_response(response)
        self.assertEqual(response["statusCode"], 201)
        self.assertTrue(body["success"])
        self.assertIn("tenant_id", body["data"])
        self.assertEqual(len(store.put_calls), 1)
        self.assertEqual(len(tenant_repo.commit_calls), 1)
        self.assertEqual(len(verification_repo.mark_used_transact_item_calls), 1)
        self.assertEqual(len(verification_repo.mark_used_calls), 0)
        self.assertEqual(len(tenant_repo.commit_calls[0]["extra_transact_items"]), 1)
        self.assertEqual(tenant_repo.commit_calls[0]["events"][0].event_type, "TenantCreatedEvent")

    def test_confirm_otp_deletes_certificate_secret_when_commit_fails(self) -> None:
        from shared.errors import OptimisticLockError
        from tests.unit.support import FakeTenantRepository

        tenant_repo = FakeTenantRepository()
        tenant_repo.commit_errors = [OptimisticLockError()]
        verification_repo = FakeVerificationRepository(_verification_for_confirm())
        validator = FakeCertificateValidator()
        store = FakeCertificateStore()
        idempotency_context = object()

        with (
            patch.object(self.handler, "_tenant_repo", return_value=tenant_repo),
            patch.object(self.handler, "_verification_repo", return_value=verification_repo),
            patch.object(
                self.handler,
                "_plan_catalog",
                return_value=FakeOnboardingPlanCatalog(self_service=True),
            ),
            patch.object(self.handler, "_certificate_validator", return_value=validator),
            patch.object(self.handler, "_certificate_store", return_value=store),
            patch.object(self.handler, "require_current_context", return_value=idempotency_context),
        ):
            response = self.handler.handler(_confirm_event(), self.context)

        self.assertEqual(response["statusCode"], 409)
        self.assertEqual(len(store.put_calls), 1)
        self.assertEqual(len(store.delete_calls), 1)
        self.assertEqual(verification_repo.mark_used_calls, [])
        self.assertEqual(len(verification_repo.mark_used_transact_item_calls), 1)

    def test_request_otp_unknown_plan_returns_404(self) -> None:
        from tests.unit.support import FakeTenantRepository

        verification_repo = FakeVerificationRepository()
        event = _request_event()

        with (
            patch.object(self.handler, "_tenant_repo", return_value=FakeTenantRepository()),
            patch.object(self.handler, "_verification_repo", return_value=verification_repo),
            patch.object(
                self.handler, "_plan_catalog", return_value=FakeOnboardingPlanCatalog(exists=False)
            ),
            patch.object(self.handler, "require_current_context", return_value=object()),
        ):
            response = self.handler.handler(event, self.context)

        body = decode_response(response)
        self.assertEqual(response["statusCode"], 404)
        self.assertEqual(body["error"]["code"], "PLAN_NOT_FOUND")
        self.assertEqual(verification_repo.commit_request_calls, [])

    def test_confirm_otp_paid_plan_includes_payment_link_in_transaction(self) -> None:
        from decimal import Decimal

        from lambdas.onboarding.domain.repositories.i_payment_verifier import CapturedPaymentInfo
        from tests.unit.support import FakeTenantRepository

        tenant_repo = FakeTenantRepository()
        verification_repo = FakeVerificationRepository(_verification_for_confirm())
        validator = FakeCertificateValidator()
        store = FakeCertificateStore()
        idempotency_context = object()

        class FakePaymentVerifier:
            def get_captured_payment(self, order_id: str) -> CapturedPaymentInfo:
                return CapturedPaymentInfo(
                    order_id=order_id,
                    payer_id="PAYER-1",
                    payer_email="buyer@example.com",
                    plan_id="plan-1",
                    amount="5.99",
                    plan_cycle="month",
                )

        class FakePaymentRepo:
            def link_tenant_transact_item(self, order_id: str, tenant_id: str) -> dict:
                return {
                    "Update": {
                        "TableName": "unit-payments",
                        "Key": {"id": f"PAYMENT#{order_id}"},
                        "UpdateExpression": "SET tenant_id = :tid",
                        "ExpressionAttributeValues": {":tid": tenant_id},
                    }
                }

        paid_catalog = FakeOnboardingPlanCatalog(
            self_service=True,
            is_free=False,
            limit_cycle="month",
        )
        paid_catalog._monthly_price = Decimal("5.99")

        with (
            patch.object(self.handler, "_tenant_repo", return_value=tenant_repo),
            patch.object(self.handler, "_verification_repo", return_value=verification_repo),
            patch.object(self.handler, "_plan_catalog", return_value=paid_catalog),
            patch.object(self.handler, "_certificate_validator", return_value=validator),
            patch.object(self.handler, "_certificate_store", return_value=store),
            patch.object(self.handler, "_payment_verifier", return_value=FakePaymentVerifier()),
            patch.object(self.handler, "DynamoPaymentRepository", return_value=FakePaymentRepo()),
            patch.object(self.handler, "_PAYMENTS_TABLE", new="unit-payments"),
            patch.object(self.handler, "require_current_context", return_value=idempotency_context),
        ):
            response = self.handler.handler(
                _confirm_event(order_id="ORDER-PAY-1"), self.context
            )

        self.assertEqual(response["statusCode"], 201)
        commit_call = tenant_repo.commit_calls[0]
        extra_items = commit_call["extra_transact_items"]
        self.assertEqual(len(extra_items), 2)
        payment_item = next(
            (i for i in extra_items if "PAYMENT#" in str(i.get("Update", {}).get("Key", {}))),
            None,
        )
        self.assertIsNotNone(payment_item, "payment link transact item missing from transaction")
        self.assertEqual(
            payment_item["Update"]["UpdateExpression"], "SET tenant_id = :tid"
        )

    def test_unknown_route_returns_404(self) -> None:
        event = api_event(method="GET", path="/does-not-exist")

        response = self.handler.handler(event, self.context)
        body = decode_response(response)

        self.assertEqual(response["statusCode"], 404)
        self.assertEqual(body["error"]["code"], "NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
