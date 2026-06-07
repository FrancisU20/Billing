"""Puertos de aplicación para email_notifications."""
from __future__ import annotations

from abc import ABC, abstractmethod


class EmailSender(ABC):
    @abstractmethod
    def send_welcome(
        self, *, email: str, nombre_rep_legal: str, temp_password: str
    ) -> None:
        """Envía el email de bienvenida al owner recién creado."""
