from __future__ import annotations

"""Application ports for email_notifications."""

from abc import ABC, abstractmethod


class EmailSender(ABC):
    @abstractmethod
    def send_welcome(self, *, email: str, legal_rep_name: str, temp_password: str) -> None:
        """Send the welcome email to the newly created owner."""
