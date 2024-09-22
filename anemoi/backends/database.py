import dataclasses
from dataclasses import asdict
from time import sleep
from typing import Dict, Optional

from peewee import CharField, Database, Model, OperationalError, Proxy, SqliteDatabase
from playhouse.db_url import connect
from playhouse.shortcuts import model_to_dict

from anemoi.backends import Backend
from anemoi.client import Client
from anemoi.util import anlog, limit_dict

db_proxy = Proxy()


class BaseModel(Model):
    class Meta:
        database = db_proxy


class ClientModel(BaseModel):
    domain = CharField(max_length=253)
    uuid = CharField(max_length=36)
    secret_key = CharField()
    last_ip4 = CharField(max_length=15)
    last_ip6 = CharField(max_length=45)


def entry_to_dataclass(entry: Model, dc):
    return dc(
        **limit_dict(model_to_dict(entry), [x.name for x in dataclasses.fields(dc)])
    )


class DatabaseBackend(Backend):
    db: Database = None

    def __init__(self, config: Dict):
        allowed_db_kinds = ["sqlite", "postgres", "mysql"]

        kind = config.get("vendor")
        connection = config.get("path")
        if kind not in allowed_db_kinds:
            raise Exception(f"Backend {kind} does not exist!")
        if kind == "sqlite":
            self.db = SqliteDatabase(connection)
        elif kind in allowed_db_kinds[1:]:
            self.db = connect(connection)
        db_proxy.initialize(self.db)
        while True:
            try:
                self.db.connect()
                break
            except OperationalError:
                anlog.error("Unable to connect to database, waiting to retry...")
                sleep(5)

        self.db.create_tables([ClientModel])

    def add_client(self, client: Client):
        ClientModel.create(**asdict(client))

    def delete_client(self, client: Client):
        c = ClientModel.delete().where(ClientModel.uuid == client.uuid)
        if c.execute():
            return client.uuid
        return None

    def get_client(
        self, uuid: Optional[str] = None, domain: Optional[str] = None
    ) -> Optional[Client]:
        res: Optional[ClientModel] = None
        if uuid:
            res = ClientModel.get_or_none(ClientModel.uuid == uuid)
        elif domain:
            res = ClientModel.get_or_none(ClientModel.domain == domain)
        if res:
            return entry_to_dataclass(res, Client)
        return None

    def update_ip(self, client: Client, ip: str, version: int):
        if version == 4:
            ClientModel.update({ClientModel.last_ip4: ip}).where(
                ClientModel.uuid == client.uuid
            ).execute()
        else:
            ClientModel.update({ClientModel.last_ip6: ip}).where(
                ClientModel.uuid == client.uuid
            ).execute()

    @property
    def clients(self):
        return [entry_to_dataclass(x, Client) for x in ClientModel.select()]
