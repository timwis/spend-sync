from typing import Optional

from prefect.blocks.core import Block
from pydantic import SecretStr
import httpx

class TrueLayerCredentials(Block):
    client_id: str
    client_secret: SecretStr
    sandbox: bool = True
    
    def _construct_base_url(self, subdomain):
        root_domain = "truelayer-sandbox.com" if self.sandbox else "truelayer.com"
        return f"https://{subdomain}.{root_domain}"

    def get_client(self, subdomain="api", access_token: Optional[str]=None) -> httpx.Client:
        base_url = self._construct_base_url(subdomain)
        headers = {"Authorization": f"Bearer {access_token}"} if access_token else {}
        client = httpx.Client(base_url=base_url, headers=headers)
        return client
        
    def get_client_id_and_secret(self):
        return {
            "client_id": self.client_id,
            "client_secret": self.client_secret.get_secret_value()
        }
