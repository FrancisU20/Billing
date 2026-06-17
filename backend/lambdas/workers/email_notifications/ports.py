from __future__ import annotations

"""Application ports for email_notifications."""

from abc import ABC, abstractmethod


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
