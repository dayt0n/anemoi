from typing import Dict, List, Optional

from cloudflare import APIError, Cloudflare
from cloudflare.types import dns, zones

from anemoi.providers import Provider
from anemoi.util import anlog, is_ip_record_valid


class CloudflareProvider(Provider):
    API: Cloudflare = None

    # parse config
    def __init__(self, config):
        try:  # noqa: SIM105
            if token := config.get("token"):
                self.API = Cloudflare(api_token=token)
            elif (email := config.get("email")) and (key := config.get("key")):
                self.API = Cloudflare(api_email=email, api_key=key)
        except APIError:
            return None

    def __get_zone_for_subdomain(self, subdomain):
        zone = ".".join(subdomain.split(".")[-2:])
        try:
            zones = self.API.zones.list(name=zone)
        except APIError as e:
            anlog.error(e)
            return None
        if len(zones.result) != 1:
            anlog.error("Could not find zone")
            return None
        return zones.result[0]

    def __get_records(self, subdomain) -> tuple[List[dns.RecordResponse], str]:
        zone: Optional[zones.Zone] = self.__get_zone_for_subdomain(subdomain)
        if zone is None:
            return []
        zid = zone.id
        try:
            recs = self.API.dns.records.list(zone_id=zid, match="all", name=subdomain)
        except APIError as e:
            anlog.error(e)
            return None, zid
        if len(recs.result) == 0:
            anlog.info(f"No records for {subdomain} found!")
            return None, zid
        # later, maybe implement something to follow CNAMEs within the same domain
        # might want to have an explicit switch for that though
        return [x for x in recs.result if x.type in ("A", "AAAA")], zid

    # returns list of {'A': '1.1.1.1'} objects
    def get_record_ips(self, subdomain) -> List[Dict[str, str]]:
        recs, _ = self.__get_records(subdomain)
        if recs:
            return [{x.type: x.content} for x in recs]
        return []

    # returns bool of if the update succeeded or not
    def update_record_ip(self, subdomain, ip, rtype="A", proxied=False) -> bool:
        if not is_ip_record_valid(ip, rtype):
            return False

        recs, zid = self.__get_records(subdomain)
        if recs:
            recs = [x for x in recs if x.type == rtype]
        if not recs:  # create new record
            try:
                self.API.dns.records.create(
                    zone_id=zid, name=subdomain, type=rtype, content=ip
                )
            except APIError as e:
                anlog.error(e)
                return False
            return True

        for rec in recs:
            if ip == rec.content:
                continue  # dont update if we dont have to
            try:
                self.API.dns.records.edit(
                    dns_record_id=rec.id,
                    zone_id=zid,
                    name=subdomain,
                    type=rec.type,
                    content=ip,
                    proxied=rec.proxied,
                )
            except APIError as e:
                anlog.error(e)
                return False
        return True
