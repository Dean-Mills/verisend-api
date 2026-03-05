"""
Keycloak Admin API service for managing user roles.

Uses the forms-api service account credentials to assign/remove
realm roles from users.
"""

import logging
from typing import Annotated

from fastapi import Depends
from keycloak import KeycloakAdmin, KeycloakOpenIDConnection

from forms.settings import settings
from forms.models.roles import Role

logger = logging.getLogger(__name__)


class KeycloakAdminService:
    """Service for managing users in Keycloak via Admin API"""
    
    def __init__(self):
        connection = KeycloakOpenIDConnection(
            server_url=settings.keycloak_server_url,
            realm_name=settings.keycloak_realm,
            client_id=settings.keycloak_client_id,
            client_secret_key=settings.keycloak_client_secret.get_secret_value(),
            verify=True,
        )
        self.admin = KeycloakAdmin(connection=connection)
    
    def assign_role(self, user_id: str, role: Role) -> None:
        """Assign a realm role to a user"""
        realm_role = self.admin.get_realm_role(role.value)
        self.admin.assign_realm_roles(user_id=user_id, roles=[realm_role])
        logger.info(f"Assigned role '{role.value}' to user {user_id}")
    
    def remove_role(self, user_id: str, role: Role) -> None:
        """Remove a realm role from a user"""
        realm_role = self.admin.get_realm_role(role.value)
        self.admin.delete_realm_roles_of_user(user_id=user_id, roles=[realm_role])
        logger.info(f"Removed role '{role.value}' from user {user_id}")


keycloak_admin_service = KeycloakAdminService()


def get_keycloak_admin() -> KeycloakAdminService:
    return keycloak_admin_service


KeycloakAdminDep = Annotated[KeycloakAdminService, Depends(get_keycloak_admin)]