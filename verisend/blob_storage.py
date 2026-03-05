from typing import Annotated, Generator
from azure.storage.blob import BlobServiceClient, ContainerClient, generate_blob_sas, BlobSasPermissions
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from forms.settings import settings
from fastapi import Depends

@contextmanager
def get_blob_storage_client() -> Generator[BlobServiceClient, None, None]:
    client = BlobServiceClient.from_connection_string(
        settings.blob_storage_connection_string.get_secret_value()
    )
    try:
        yield client
    finally:
        client.close()

def get_blob_container() -> Generator[ContainerClient, None, None]:
    with get_blob_storage_client() as client:
        container = client.get_container_client(settings.blob_storage_container_name)
        
        # Check if container exists, create if not
        if not container.exists():
            container.create_container()
        
        yield container

BlobStorageContainer = Annotated[ContainerClient, Depends(get_blob_container)]

def generate_sas_url(
    blob_url: str,
    container: ContainerClient,
    expires_in_minutes: int = 60
) -> str:
    """Generate a read-only SAS URL for a blob."""
    blob_name = blob_url.split(f"{container.container_name}/")[-1]
    
    sas_token = generate_blob_sas(
        account_name=container.account_name,
        container_name=container.container_name,
        blob_name=blob_name,
        account_key=container.credential.account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes),
    )
    
    return f"{blob_url}?{sas_token}"