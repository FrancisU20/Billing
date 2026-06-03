from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class EmailMessage:
    to: str
    subject: str
    html_body: str
    attachments: list[dict]  # [{"filename": "...", "content": bytes, "content_type": "..."}]
    from_name: str = "CodeLabs Billing"
    from_email: str = "facturacion@codelabsecuador.com"
    reply_to: str | None = None


class EmailProvider(ABC):
    name: str

    @abstractmethod
    def send(self, message: EmailMessage) -> bool:
        """Envía el email. Retorna True si fue exitoso."""
        ...
