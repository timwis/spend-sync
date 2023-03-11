from typing import Optional

from prefect.blocks.core import Block
from pydantic import SecretStr
import httpx

BASE_URL = "https://api.monzo.com"

class MonzoCredentials(Block):
    client_id: str
    client_secret: SecretStr

    def get_client(self, access_token: Optional[str]=None) -> httpx.Client:
        headers = {"Authorization": f"Bearer {access_token}"} if access_token else {}
        client = httpx.Client(base_url=BASE_URL, headers=headers)        
        return client
    
    def get_client_id_and_secret(self):
        return {
            "client_id": self.client_id,
            "client_secret": self.client_secret.get_secret_value()
        }
