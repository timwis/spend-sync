import datetime
from operator import itemgetter
import os

import httpx
from prefect import flow, task
from prefect_sqlalchemy import SqlAlchemyConnector
from sqlalchemy.orm import sessionmaker, joinedload
from true_layer import TrueLayer

from models import JobDefinition, Account, Connection

DEBUG = True if os.getenv("DEBUG") else False
database_block = SqlAlchemyConnector.load("db")
Session = sessionmaker(database_block.get_engine(echo=DEBUG), expire_on_commit=False)
truelayer_block = TrueLayer.load("truelayer")

def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)

@task()
def get_job_definitions():
    with Session() as session:
        query = session.query(JobDefinition).options(
            joinedload(JobDefinition.card_account) \
            .joinedload(Account.connection)
        # TODO: .where(...) # last synced > 24 hr ago or null
        )
        return query.all()

@task()
def get_card_transactions(account, since=None):
    truelayer_account_id = account.truelayer_account_id
    access_token = account.connection.decrypted_access_token
    since = since or (now_utc() - datetime.timedelta(1)).isoformat(timespec="seconds")

    url = truelayer_block.url("api", f"/data/v1/cards/{truelayer_account_id}/transactions")
    params = {"from": since, "to": now_utc().isoformat(timespec="seconds")}
    headers = {"Authorization": f"Bearer {access_token}"}
    response = httpx.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()["results"]

@task
def renew_token(connection: Connection):
    refresh_token = connection.decrypted_refresh_token
    return truelayer_block.get_renewed_token(refresh_token)

@task
def save_renewed_token(connection: Connection, renewed_token):
    access_token, expires_in, refresh_token = itemgetter('access_token', 'expires_in', 'refresh_token')(renewed_token)

    with Session() as session:
        connection.access_token = access_token
        connection.refresh_token = refresh_token
        connection.expires_at = now_utc() + datetime.timedelta(0, expires_in)
        session.add(connection)
        session.commit()
        session.refresh(connection)

@flow()
def sync():
    job_definitions = get_job_definitions()

    results = []
    for jd in job_definitions:
        if jd.card_account.connection.expires_at <= now_utc():
            renewed_token = renew_token(jd.card_account.connection)
            save_renewed_token(renewed_token)

        card_transactions = get_card_transactions(jd.card_account, jd.last_synced_at)
        total = sum([txn["amount"] for txn in card_transactions])
        results.append(total)
    return results

if __name__ == "__main__":
    print(sync())
