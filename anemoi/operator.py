from secrets import choice, token_urlsafe
from typing import Optional
from uuid import uuid4

import bcrypt

from anemoi.backends import Backend
from anemoi.client import Client
from anemoi.util import hash_password, ip_version


class ClientOperator:
    backend: Backend

    def __init__(self, backend):
        self.backend = backend

    def new_client(self, domain, firstIP4="", firstIP6="") -> tuple[Client, str]:
        aID = str(uuid4())
        # bcrypt max length is 72 characters
        # generate a random string that is URL safe/printable but also has a length between 64 and 72 bytes
        aSecret = token_urlsafe(64)[: choice(range(64, 72))]
        # firstIP can be blank
        client = Client(domain, aID, hash_password(aSecret), firstIP4, firstIP6)
        self.backend.add_client(client)
        return client, aSecret

    def validate_secret(self, uuid, secret):
        if client := self.backend.get_client(uuid=uuid):
            return bcrypt.checkpw(secret.encode(), client.secret_key.encode())
        return False

    def delete_client(
        self, uuid: Optional[str] = None, domain: Optional[str] = None
    ) -> Optional[str]:
        if client := self.backend.get_client(uuid=uuid, domain=domain):
            deleted_uuid = self.backend.delete_client(client)
            return deleted_uuid
        return None

    @property
    def clients(self):
        return self.backend.clients

    def update_ip(self, uuid: str, ip: str):
        if client := self.backend.get_client(uuid=uuid):
            self.backend.update_ip(client, ip, ip_version(ip))

    def did_ip_change(self, uuid, ip) -> bool:
        if client := self.backend.get_client(uuid=uuid):
            if ip_version(ip) == 4:
                return client.last_ip4 != ip
            else:
                return client.last_ip6 != ip
        return False
