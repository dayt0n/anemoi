from typing import Dict, List

import CloudFlare
import CloudFlare.exceptions

from anemoi.providers import Provider
from anemoi.util import anlog, is_ip_record_valid


class CloudflareProvider(Provider):
    API: CloudFlare.CloudFlare = None

    # parse config
    def __init__(self, config):
        try:  # noqa: SIM105
            if token := config.get("token"):
                self.API = CloudFlare.CloudFlare(token=token)
            elif (email := config.get("email")) and (key := config.get("key")):
                self.API = CloudFlare.CloudFlare(email=email, key=key)
        except CloudFlare.exceptions.CloudFlareAPIError:
            return None

    def __get_zone_for_subdomain(self, subdomain):
        zone = ".".join(subdomain.split(".")[-2:])
        try:
            zones = self.API.zones.get(params={"name": zone})
        except CloudFlare.exceptions.CloudFlareAPIError as e:
            anlog.error(e)
            return None
        if len(zones) != 1:
            anlog.error("Could not find zone")
            return None
        return zones[0]

    def __get_records(self, subdomain) -> tuple[List[str], str]:
        zone = self.__get_zone_for_subdomain(subdomain)
        zid = zone["id"]
        try:
            recs = self.API.zones.dns_records.get(
                zid, params={"name": subdomain, "match": "all"}
            )
        except CloudFlare.exceptions.CloudFlareAPIError as e:
            anlog.error(e)
            return None, zid
        if len(recs) == 0:
            anlog.info(f"No records for {subdomain} found!")
            return None, zid
        # later, maybe implement something to follow CNAMEs within the same domain
        # might want to have an explicit switch for that though
        return [x for x in recs if x["type"] in ("A", "AAAA")], zid

    # returns list of {'A': '1.1.1.1'} objects
    def get_record_ips(self, subdomain) -> List[Dict[str, str]]:
        recs, _ = self.__get_records(subdomain)
        if recs:
            return [{x["type"]: x["content"]} for x in recs]
        return []

    # returns bool of if the update succeeded or not
    def update_record_ip(self, subdomain, ip, rtype="A", proxied=False) -> bool:
        if not is_ip_record_valid(ip, rtype):
            return False

        recs, zid = self.__get_records(subdomain)
        if recs:
            recs = [x for x in recs if x["type"] == rtype]
        if not recs:  # create new record
            try:
                self.API.zones.dns_records.post(
                    zid, data={"name": subdomain, "type": rtype, "content": ip}
                )
            except CloudFlare.exceptions.CloudFlareAPIError as e:
                anlog.error(e)
                return False
            return True

        for rec in recs:
            if ip == rec["content"]:
                continue  # dont update if we dont have to
            try:
                self.API.zones.dns_records.put(
                    zid,
                    rec["id"],
                    data={
                        "name": subdomain,
                        "type": rec["type"],
                        "content": ip,
                        "proxied": rec["proxied"],
                    },
                )
            except CloudFlare.exceptions.CloudFlareAPIError as e:
                anlog.error(e)
                return False
        return True
