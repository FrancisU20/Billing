"""
Decorator @require_role para control de acceso por rol.

Debe usarse DESPUÉS de @lambda_handler (orden de decoradores: de abajo hacia arriba).

Roles disponibles (definidos en Cognito custom:role):
    superadmin  — acceso global, omite la verificación de rol
    owner       — dueño del tenant
    admin       — administrador del tenant
    viewer      — solo lectura

Uso:
    @lambda_handler
    @require_role("owner", "admin")
    def handler(request: Request, context) -> dict:
        ...
"""
import functools
from typing import Callable

from shared.errors import ForbiddenError


def require_role(*allowed_roles: str) -> Callable:
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(request, context):
            if request.is_superadmin:
                return func(request, context)
            if request.role not in allowed_roles:
                raise ForbiddenError(
                    f"rol '{request.role}' no tiene acceso — requerido: {allowed_roles}"
                )
            return func(request, context)
        return wrapper
    return decorator
