import importlib
from typing import Dict, List, Optional

from anemoi.client import Client


class Backend:
    def __init__(self, config: Dict):
        # do something with your {'type':'aaa', 'vendor': 'bbb', 'path': 'ccc'} config here
        pass

    def add_client(self, client: Client):
        pass

    # return UUID if success, None if fail
    def delete_client(self, client: Client) -> Optional[str]:
        return None

    # return Client() object if success, None if fail
    def get_client(
        self, uuid: Optional[str] = None, domain: Optional[str] = None
    ) -> Optional[Client]:
        return None

    def update_ip(self, client: Client, ip: str, version: int):
        pass

    @property
    def clients(self) -> List[Client]:
        return []


def init_backend(
    config: Dict,
    default_type="tinydb",
    default_vendor="tinydb",
    default_path="~/.anemoi/clients.json",
) -> Backend:
    default_backend = {
        "type": default_type,
        "vendor": default_vendor,
        "path": default_path,
    }
    backend_config = default_backend | config.get("backend", default_backend)
    if backend_config["type"] == "database" and backend_config["vendor"] == "tinydb":
        raise Exception(
            f"Incompatible backend type and vendor. Make sure vendor is correct for the type '{backend_config['type']}"
        )
    backend_obj: Optional[Backend] = getattr(
        importlib.import_module(f"anemoi.backends.{backend_config['type']}"),
        f"{backend_config['type'].capitalize()}Backend",
    )
    if not backend_obj:
        raise ModuleNotFoundError(
            f"No backend named {backend_config['vendor'].capitalize()}"
        )
    return backend_obj(backend_config)
