import datetime

from pydantic import SecretStr, BaseModel
from prefect import task
from prefect_monzo.credentials import MonzoCredentials

class Token(BaseModel):
  access_token: SecretStr
  refresh_token: SecretStr
  expires_in: int

class Money:
  def __init__(self, major: float):
    self.value = int(major * 100)

  def as_minor(self):
    return self.value

@task
def renew_monzo_token(
    credentials: MonzoCredentials,
    refresh_token: str
) -> Token:
  url = "/oauth2/token"
  client_id_and_secret = credentials.get_client_id_and_secret()
  data = client_id_and_secret | {
    "grant_type": "refresh_token",
    "refresh_token": refresh_token
  }
  client = credentials.get_client()
  response = client.post(url, data=data)
  response.raise_for_status()
  response_data = response.json()
  return Token(*response_data)

@task
def deposit_into_pot(
  credentials: MonzoCredentials,
  access_token: str,
  source_account_id: str,
  destination_pot_id: str,
  amount: Money
):
  url = f"/pots/{destination_pot_id}/deposit"
  dedupe_id = f"{datetime.date.today().isoformat()}-{amount.as_minor()}"
  data = {
    "source_account_id": source_account_id,
    "amount": amount.as_minor(),
    "dedupe_id": dedupe_id
  }

  client = credentials.get_client(access_token=access_token)
  response = client.put(url, data=data)
  response.raise_for_status()
  response_data = response.json()
  return response_data
