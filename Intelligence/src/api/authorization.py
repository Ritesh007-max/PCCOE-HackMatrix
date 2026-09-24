"""
FIN Lightweight Role-Based Authorization Model.
Defines role semantics (CITIZEN, SERVICE, ADMIN, REVIEWER) and dependency guards
to protect sensitive operations (e.g. policy synchronization, rollback) while
maintaining compatibility with future BackEnd authentication layers.
"""

from enum import Enum
import logging
from typing import Callable, List, Optional, Set
from fastapi import Depends, Header, HTTPException, status

from .auth import verify_service_api_key

logger = logging.getLogger("fin.api.authorization")


class Role(str, Enum):
    """Authorized participant roles within FIN ecosystem."""
    CITIZEN = "citizen"
    REVIEWER = "reviewer"
    SERVICE = "service"
    ADMIN = "admin"

    @classmethod
    def from_header(cls, val: Optional[str]) -> "Role":
        if not val:
            # Default for trusted internal service-to-service callers
            return cls.ADMIN
        normalized = val.strip().lower()
        for r in cls:
            if r.value == normalized:
                return r
        return cls.CITIZEN  # Fail-safe default on unrecognized role strings


# Mapping of roles to inherited capabilities
ROLE_HIERARCHY = {
    Role.ADMIN: {Role.ADMIN, Role.REVIEWER, Role.SERVICE, Role.CITIZEN},
    Role.SERVICE: {Role.SERVICE, Role.CITIZEN},
    Role.REVIEWER: {Role.REVIEWER, Role.CITIZEN},
    Role.CITIZEN: {Role.CITIZEN},
}


def get_current_role(
    x_ai_role: Optional[str] = Header(None, alias="X-AI-Role", description="Caller role declaration"),
    api_key: str = Depends(verify_service_api_key),
) -> Role:
    """
    Extracts and validates caller role.
    Requires valid service authentication before evaluating role permissions.
    """
    role = Role.from_header(x_ai_role)
    return role


def require_role(*required_roles: Role) -> Callable:
    """
    FastAPI dependency factory enforcing that the authenticated caller possesses
    at least one of the required roles or a parent role in the hierarchy.
    """
    def role_checker(
        current_role: Role = Depends(get_current_role),
    ) -> Role:
        allowed_capabilities = ROLE_HIERARCHY.get(current_role, {current_role})
        
        has_permission = any(req in allowed_capabilities for req in required_roles)
        if not has_permission:
            req_names = ", ".join(r.value.upper() for r in required_roles)
            logger.warning(
                "Access denied: Caller role '%s' lacks required role(s) [%s]",
                current_role.value, req_names
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: Insufficient privileges. Required role: {req_names}.",
            )
        return current_role

    return role_checker


# Convenient role dependency presets
require_admin = require_role(Role.ADMIN)
require_reviewer = require_role(Role.REVIEWER, Role.ADMIN)
require_service = require_role(Role.SERVICE, Role.ADMIN)
require_citizen = require_role(Role.CITIZEN, Role.SERVICE, Role.REVIEWER, Role.ADMIN)
