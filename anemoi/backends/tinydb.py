from dataclasses import asdict
from typing import Dict, Optional

from tinydb import Query, TinyDB

from anemoi.client import Client

from . import Backend


class TinydbBackend(Backend):
    db: TinyDB

    def __init__(self, config: Dict):
        self.db = TinyDB(config.get("path"))

    def add_client(self, client: Client):
        self.db.insert(asdict(client))

    def delete_client(self, client: Client):
        client_query = Query()
        res = self.db.search(client_query.domain == client.domain)
        if len(res) == 1:
            client = Client(**res[0])
            res = self.db.remove(doc_ids=[res[0].doc_id])
            if len(res) == 1:
                return client.uuid
        return None

    def get_client(self, uuid=None, domain=None) -> Optional[Client]:
        client_query = Query()
        res = []
        if uuid:
            res = self.db.search(client_query.uuid == uuid)
        elif domain:
            res = self.db.search(client_query.domain == domain)
        if len(res) == 1:
            return Client(**res[0])
        return None

    def update_ip(self, client: Client, ip: str, version: int):
        client_query = Query()
        ip_key = "last_ip4" if version == 4 else "last_ip6"

        self.db.update({ip_key: ip}, (client_query.uuid == client.uuid))

    @property
    def clients(self):
        return [Client(**x) for x in self.db.all()]
