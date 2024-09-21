import importlib
from typing import Dict, List, Optional

from anemoi.util import anlog, get_or_parse_yaml


class Provider:
    def __init__(self, config):
        pass

    # returns list of {'A': '1.1.1.1'} objects
    def get_record_ips(self, subdomain) -> List[Dict[str, str]]:
        return []

    # returns bool of if the update succeeded or not
    def update_record_ip(self, subdomain, ip, rtype="A", **kwargs) -> bool:
        return False


class Providers:
    providers: Dict[str, Provider]

    def __init__(self, config_file):
        self.providers = {}
        conf = get_or_parse_yaml(config_file)
        for domain_config in conf.get("domains", []):
            provider_name = domain_config.get("provider", "")
            zone = domain_config.get("zone")
            provider_obj: Optional[Provider] = getattr(
                importlib.import_module(f"anemoi.providers.{provider_name}"),
                f"{provider_name.capitalize()}Provider",
            )
            if not provider_obj:
                raise ModuleNotFoundError(
                    f"No DNS provider named {provider_name.capitalize()}"
                )
            provider = provider_obj(domain_config)
            if not provider:
                anlog.error(
                    f"Unable to authenticate on {provider_name.capitalize()} for {zone}"
                )
                continue
            self.providers.update({zone: provider})

    def get_provider(self, zone) -> Optional[Provider]:
        if zone.count(".") > 1:
            zone = ".".join(zone.split(".")[-2:])
        return self.providers.get(zone)
