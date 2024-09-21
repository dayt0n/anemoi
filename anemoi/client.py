from dataclasses import dataclass


@dataclass
class Client:
    domain: str
    uuid: str
    secret_key: str
    last_ip4: str
    last_ip6: str
