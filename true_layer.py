from urllib.parse import urljoin

from prefect.blocks.core import Block
from pydantic import SecretStr
import httpx

class TrueLayer(Block):
    client_id: str
    client_secret: SecretStr
    redirect_uri: str
    sandbox: bool = True

    def url(self, subdomain, path):
        domain = "truelayer-sandbox.com" if self.sandbox else "truelayer.com"
        base_url = f"https://{subdomain}.{domain}"
        return urljoin(base_url, path)
      
    def get_renewed_token(self, refresh_token):
        url = self.url("auth", "/connect/token")
        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret.get_secret_value(),
            "redirect_uri": self.redirect_uri,
            "refresh_token": refresh_token
        }
        print(data)
        response = httpx.post(url, data=data)
        response.raise_for_status()
        return response.json()
