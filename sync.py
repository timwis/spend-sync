import datetime
import os

from pydantic import SecretStr, BaseModel
import httpx
from prefect import flow, task
from prefect_sqlalchemy import SqlAlchemyConnector
from sqlalchemy import or_
from sqlalchemy.orm import sessionmaker, joinedload

from prefect_true_layer import TrueLayerCredentials
import prefect_true_layer.tasks
from prefect_monzo import MonzoCredentials
import prefect_monzo.tasks
from models import JobDefinition, Account, Connection

DEBUG = True if os.getenv("DEBUG") else False
database_block = SqlAlchemyConnector.load("db")
Session = sessionmaker(database_block.get_engine(echo=DEBUG), expire_on_commit=False)
true_layer_credentials = TrueLayerCredentials.load("truelayer")
monzo_credentials = MonzoCredentials.load("monzo")

class Token(BaseModel):
  access_token: SecretStr
  refresh_token: SecretStr
  expires_in: int

class Money:
  def __init__(self, major: float):
    self.value = int(major * 100)

  def as_minor(self):
    return self.value

def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)

@task()
def get_job_definitions():
    one_day_ago = now_utc() - datetime.timedelta(days=1)
    with Session() as session:
        query = session.query(JobDefinition).options(
            joinedload(JobDefinition.card_account) \
            .joinedload(Account.connection)
        ).options(
            joinedload(JobDefinition.cash_account) \
            .joinedload(Account.connection)
        ).options(
            joinedload(JobDefinition.reserve_account)
            .joinedload(Account.connection)
        ).filter(or_(
           JobDefinition.last_synced_at < one_day_ago,
           JobDefinition.last_synced_at == None
        ))
        return query.all()

@task
def save_renewed_token(connection: Connection, renewed_token: Token):
    access_token = renewed_token.access_token
    refresh_token = renewed_token.refresh_token
    expires_in = renewed_token.expires_in

    with Session() as session:
        connection.access_token = access_token.get_secret_value()
        connection.refresh_token = refresh_token.get_secret_value()
        connection.expires_at = now_utc() + datetime.timedelta(0, expires_in)
        session.add(connection)
        session.commit()
        session.refresh(connection)

@task
def update_last_synced(job_definition: JobDefinition):
   with Session() as session:
      job_definition.last_synced_at = now_utc()
      session.add(job_definition)
      session.commit()

@flow()
def sync():
    job_definitions = get_job_definitions()

    results = []
    for job_def in job_definitions:
        card_connection = job_def.card_account.connection

        try:
            if card_connection.expires_at <= now_utc():
                renewed_token = prefect_true_layer.tasks.renew_true_layer_token(
                    credentials=true_layer_credentials,
                    refresh_token=card_connection.decrypted_refresh_token)
                save_renewed_token(card_connection, renewed_token)

            card_transactions = prefect_true_layer.tasks.get_card_transactions(
                credentials=true_layer_credentials,
                account_id=job_def.card_account.external_account_id,
                access_token=card_connection.decrypted_access_token,
                since=job_def.last_synced_at)

            total = sum([txn["amount"] for txn in card_transactions])
            print(f"Spent {total}")
            amount_to_sync = Money(major=total)

            cash_connection = job_def.cash_account.connection

            if cash_connection.expires_at <= now_utc():
                renewed_token = prefect_monzo.tasks.renew_monzo_token(
                    credentials=monzo_credentials,
                    refresh_token=cash_connection.decrypted_refresh_token
                )
                save_renewed_token(cash_connection, renewed_token)

            deposit_result = prefect_monzo.tasks.deposit_into_pot(
                credentials=monzo_credentials,
                access_token=cash_connection.decrypted_access_token,
                source_account_id=job_def.cash_account.external_account_id,
                destination_pot_id=job_def.reserve_account.external_account_id,
                amount=amount_to_sync
            )
            results.append(deposit_result)

            update_last_synced(job_def)
        except httpx.HTTPStatusError as err:
           print(err.response.text)
           raise err

    return results

if __name__ == "__main__":
    print(sync())
