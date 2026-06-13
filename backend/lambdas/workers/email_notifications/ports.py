from __future__ import annotations

"""Application ports for email_notifications."""

from abc import ABC, abstractmethod


class EmailSender(ABC):
    @abstractmethod
    def send_welcome(self, *, email: str, legal_rep_name: str, temp_password: str) -> None:
        """Send the welcome email to the newly created owner."""

    @abstractmethod
    def send_enterprise_lead_notification(
        self, *, superadmin_email: str, trade_name: str, ruc: str, email: str, plan_id: str
    ) -> None:
        """Notify the sales team about a new Enterprise lead capture."""
