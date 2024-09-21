from dataclasses import asdict
from typing import Dict, Optional

from peewee import CharField, Database, Model, PostgresqlDatabase, Proxy, SqliteDatabase
from playhouse.shortcuts import model_to_dict

from anemoi.backends import Backend
from anemoi.client import Client

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


class DatabaseBackend(Backend):
    db: Database = None

    def __init__(self, config: Dict):
        kind = config.get("kind")
        connection = config.get("connection")
        if kind not in ("sqlite", "postgres"):
            raise Exception(f"Backend {kind} does not exist!")
        if kind == "sqlite":
            self.db = SqliteDatabase(connection)
        elif kind == "postgres":
            self.db = PostgresqlDatabase(connection)
        db_proxy.initialize(self.db)
        self.db.connect()
        self.db.create_tables()

    def add_client(self, client: Client):
        ClientModel.create(**asdict(client))

    @db.atomic()
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
            res = ClientModel.get_or_none(ClientModel.uuid == uuid).execute()
        elif domain:
            res = ClientModel.get_or_none(ClientModel.domain == domain).execute()
        if res:
            return Client(**model_to_dict(res))
        return None

    def update_ip(self, client: Client, ip: str, kind: str):
        if kind == "4":
            ClientModel.update({ClientModel.last_ip4: ip}).where(
                ClientModel.uuid == client.uuid
            ).execute()
        else:
            ClientModel.update({ClientModel.last_ip6: ip}).where(
                ClientModel.uuid == client.uuid
            ).execute()

    @property
    def clients(self):
        return [Client(**model_to_dict(x)) for x in ClientModel.select()]
