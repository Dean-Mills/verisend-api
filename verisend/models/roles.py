from enum import Enum

class Role(str, Enum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    PUBLISHER = "publisher"
    USER = "user"
    
    @classmethod
    def from_keycloak_roles(cls, roles: list[str]) -> "Role":
        """Get highest privilege role from Keycloak role list"""
        if "super_admin" in roles:
            return cls.SUPER_ADMIN
        if "admin" in roles:
            return cls.ADMIN
        if "publisher" in roles:
            return cls.PUBLISHER
        return cls.USER