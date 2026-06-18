from __future__ import annotations

"""Application ports for email_notifications."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentAttachments:
    xml_content: bytes
    xml_filename: str
    ride_content: bytes
    ride_filename: str


class DocumentAttachmentReader(ABC):
    @abstractmethod
    def get_authorized_document(
        self, *, xml_s3_key: str, ride_s3_key: str, document_id: str
    ) -> DocumentAttachments:
        """Load the authorized XML and RIDE PDF for buyer delivery."""


class EmailSender(ABC):
    @abstractmethod
    def send_onboarding_otp(
        self,
        *,
        email: str,
        legal_rep_name: str,
        otp: str,
        expires_at: str,
    ) -> None:
        """Send the public onboarding email verification code."""

    @abstractmethod
    def send_welcome(self, *, email: str, legal_rep_name: str, temp_password: str) -> None:
        """Send the welcome email to the newly created owner."""

    @abstractmethod
    def send_enterprise_lead_notification(
        self, *, superadmin_email: str, trade_name: str, ruc: str, email: str, plan_id: str
    ) -> None:
        """Notify the sales team about a new Enterprise lead capture."""

    @abstractmethod
    def send_certificate_expiry_alert(
        self,
        *,
        email: str,
        legal_rep_name: str,
        trade_name: str,
        ruc: str,
        cert_expires_at: str,
        days_remaining: int,
    ) -> None:
        """Warn the tenant that its digital certificate is about to expire."""

    @abstractmethod
    def send_subscription_renewal_reminder(
        self,
        *,
        email: str,
        legal_rep_name: str,
        trade_name: str,
        plan_cycle_ends_at: str,
        days_remaining: int,
        renewal_url: str,
    ) -> None:
        """Remind the tenant to renew their subscription before it expires."""

    @abstractmethod
    def send_subscription_expired(
        self,
        *,
        email: str,
        legal_rep_name: str,
        trade_name: str,
        renewal_url: str,
    ) -> None:
        """Notify the tenant that their subscription has expired and access is suspended."""

    @abstractmethod
    def send_payment_failed(
        self,
        *,
        email: str,
        legal_rep_name: str,
        trade_name: str,
        renewal_url: str,
    ) -> None:
        """Notify the tenant that their automatic recurring payment failed."""

    @abstractmethod
    def send_document_authorized(
        self,
        *,
        email: str,
        legal_rep_name: str,
        document_id: str,
        access_key: str,
        authorization_number: str,
        issuer_name: str,
        issuer_ruc: str,
        buyer_name: str,
        buyer_id: str,
        buyer_email: str,
        sequential_display: str,
        issued_at: str,
        authorized_at: str,
        total: str,
        currency: str,
    ) -> None:
        """Notify the tenant that a document was authorized by the SRI."""

    @abstractmethod
    def send_document_rejected(
        self,
        *,
        email: str,
        legal_rep_name: str,
        document_id: str,
        access_key: str,
        sri_errors: list[dict],
    ) -> None:
        """Notify the tenant that a document was rejected by the SRI."""

    @abstractmethod
    def send_document_failed_permanent(
        self,
        *,
        email: str,
        legal_rep_name: str,
        document_id: str,
        access_key: str,
    ) -> None:
        """Notify the tenant that authorization could not be confirmed after retries."""

    @abstractmethod
    def send_document_to_buyer(
        self,
        *,
        email: str,
        buyer_name: str,
        document_id: str,
        access_key: str,
        authorization_number: str,
        issuer_name: str,
        issuer_ruc: str,
        buyer_id: str,
        issued_at: str,
        authorized_at: str,
        total: str,
        currency: str,
        xml_content: bytes,
        xml_filename: str,
        ride_content: bytes,
        ride_filename: str,
    ) -> None:
        """Send the authorized XML and RIDE PDF to the invoice buyer."""

    @abstractmethod
    def send_orphan_payment_alert(
        self,
        *,
        superadmin_email: str,
        order_id: str,
        payer_email: str | None,
        plan_id: str,
        amount: str,
        currency: str,
        confirmed_at: str,
    ) -> None:
        """Alert the superadmin about a PAID payment with no associated tenant."""
