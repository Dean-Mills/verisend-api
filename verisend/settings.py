from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr

from pydantic_settings import BaseSettings
import urllib.parse

class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env"),
    )

    api_key: SecretStr
    datalab_api_key: SecretStr
    openai_api_key: SecretStr

    mistral_api_key: SecretStr
    gemini_api_key: SecretStr
    
    keycloak_server_url: str
    keycloak_realm: str
    keycloak_client_id: str
    keycloak_client_secret: SecretStr
    
    db_pool_size: int = 20
    db_connection_string: Optional[SecretStr] = None
    db_user: SecretStr
    db_database: str
    db_password: SecretStr
    db_host: str
    db_port: str = "5432"
    
    blob_storage_connection_string: SecretStr
    blob_storage_container_name: str
    
    @property
    def db_conn_str(self):
        if self.db_connection_string is not None:
            return self.db_connection_string.get_secret_value()
        
        return (
            f"postgresql://"
            f"{urllib.parse.quote(self.db_user.get_secret_value())}:"
            f"{urllib.parse.quote(self.db_password.get_secret_value())}@"
            f"{self.db_host}:{self.db_port}/{self.db_database}"
        )

settings = AppSettings() # type: ignore
