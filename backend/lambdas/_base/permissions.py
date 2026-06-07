from __future__ import annotations
"""
@require_role decorator for role-based access control.

Must be used AFTER @lambda_handler (decorator order: bottom to top).

Available roles (defined in Cognito custom:role):
    superadmin  — global access, skips the role check
    owner       — tenant owner
    admin       — tenant administrator
    viewer      — read only

Usage:
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
                    f"role '{request.role}' has no access — required: {allowed_roles}"
                )
            return func(request, context)
        return wrapper
    return decorator
