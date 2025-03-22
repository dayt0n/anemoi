import json
import logging
import socket
from typing import Dict, Optional, Union

import bcrypt
import requests
import yaml
from jsonschema import validate

anlog = logging.getLogger("anlog")


def set_loglevel(v):
    ch = logging.StreamHandler()
    if v:
        anlog.setLevel(logging.DEBUG)
        ch.setFormatter(logging.Formatter("%(levelname)s - %(msg)s"))
    else:
        anlog.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter("%(message)s"))
    anlog.addHandler(ch)


def limit_dict(dictionary, keys: tuple, translation: Optional[tuple] = None) -> Dict:
    result = {}
    if not isinstance(dictionary, Dict):
        return result
    for i, k in enumerate(keys):
        if k in dictionary:
            if translation:
                result.update({translation[i]: dictionary[k]})
            else:
                result.update({k: dictionary[k]})
    return result


def get_my_public_ip():
    r = requests.get("https://ipinfo.io/ip")
    if r.status_code == 200:
        return r.text.strip()
    return None


def hash_password(passwd):
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(passwd.encode(), salt).decode()


def is_ip_record_valid(ip: str, rtype: str):
    if (ip_version(ip) == 6 and rtype != "AAAA") or (
        ip_version(ip) == 4 and rtype != "A"
    ):
        anlog.error("IP type mismatch")
        return False
    return True


def ip_version(ip: str) -> int:
    try:
        socket.inet_aton(ip)
        return 4
    except Exception:
        socket.inet_pton(socket.AF_INET6, ip)
        return 6


def record_type(ip: str):
    return "AAAA" if ip_version(ip) == 6 else "A"


config_schema = """
{
    "type": "object",
    "additionalProperties": false,
    "properties": {
        "domains": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": true,
                "properties": {
                    "zone": {
                        "type": "string"
                    },
                    "provider": {
                        "type": "string"
                    }
                },
                "required": [
                    "provider",
                    "zone"
                ]
            }
        },
        "backend": {
            "type": "object",
            "additionalProperties": false,
            "properties": {
                "type": {
                    "type": "string"
                },
                "vendor": {
                    "type": "string"
                },
                "path": {
                    "type": "string"
                }
            },
            "required": [
                "path",
                "type"
            ]
        }
    },
    "required": [
        "backend",
        "domains"
    ]
}
"""


def get_or_parse_yaml(data: Union[Dict, str]) -> Dict:
    if isinstance(data, str):
        with open(data, "r") as fp:
            data = yaml.safe_load(fp.read())
            validate(data, json.loads(config_schema))
    return data
