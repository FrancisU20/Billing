"""
OnboardTenantUseCase — crea el usuario owner en Cognito.

Recibe el payload del TenantCreatedEvent y:
1. Genera una contraseña temporal
2. Crea el usuario en Cognito con rol 'owner' y el tenant_id correcto
3. Retorna la contraseña temporal para que el handler publique OwnerCreatedEvent
   → email_notifications worker la usa para enviar el email de bienvenida via Brevo

Si el usuario ya existe retorna None — el email no se reenvía.
"""
from __future__ import annotations

import secrets
import string

from lambdas.workers.tenant_onboarding.ports import IdentityProvider
from shared.errors import InternalError, ValidationError
from shared.logger import get_logger

_log = get_logger(__name__)

_PASSWORD_CHARS = string.ascii_letters + string.digits + "!@#$%^&*"


def _generate_temp_password(length: int = 16) -> str:
    while True:
        pwd = "".join(secrets.choice(_PASSWORD_CHARS) for _ in range(length))
        if (
            any(c.isupper() for c in pwd)
            and any(c.islower() for c in pwd)
            and any(c.isdigit() for c in pwd)
            and any(c in "!@#$%^&*" for c in pwd)
        ):
            return pwd


class OnboardTenantUseCase:
    def __init__(self, identity_provider: IdentityProvider) -> None:
        self._identity_provider = identity_provider

    def execute(
        self, tenant_id: str, email: str, nombre_rep_legal: str
    ) -> str | None:
        """
        Retorna temp_password si el owner fue creado, None si ya existía.
        La contraseña nunca se loguea — viaja en memoria hasta publicarse en SQS SSE.
        """
        if not tenant_id or not email:
            raise ValidationError("tenant_id y email son requeridos para onboarding")

        temp_password = _generate_temp_password()

        try:
            created = self._identity_provider.create_owner(
                tenant_id=tenant_id,
                email=email,
                temporary_password=temp_password,
            )
        except Exception as e:
            _log.error("error creando usuario en Cognito", error=str(e), exc_info=True)
            raise InternalError()

        if not created:
            return None

        _log.info("tenant onboarding completado", tenant_id=tenant_id, email=email)
        return temp_password
