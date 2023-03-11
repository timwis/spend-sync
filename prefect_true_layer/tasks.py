import datetime

from pydantic import SecretStr, BaseModel
from prefect import task
from prefect_true_layer.credentials import TrueLayerCredentials

class Token(BaseModel):
    access_token: SecretStr
    refresh_token: SecretStr
    expires_in: int

@task
def renew_true_layer_token(
    credentials: TrueLayerCredentials,
    refresh_token: str
) -> Token:
    url = "/connect/token"
    client_id_and_secret = credentials.get_client_id_and_secret()
    data = client_id_and_secret | {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }
    client = credentials.get_client("auth")
    response = client.post(url, data=data)
    response.raise_for_status()
    response_data = response.json()
    return Token(**response_data)

@task
def get_card_transactions(
  credentials: TrueLayerCredentials,
  account_id: str,
  access_token: str,
  since: datetime.datetime = None
):
    url = f"/data/v1/cards/{account_id}/transactions"
    since = since or one_day_ago().isoformat(timespec="seconds")
    params = {
        "from": since,
        "to": now_utc().isoformat(timespec="seconds")
    }
    client = credentials.get_client(access_token=access_token)
    response = client.get(url, params=params)
    response.raise_for_status()
    return response.json()["results"]

def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)

def one_day_ago():
    return now_utc() - datetime.timedelta(1)
