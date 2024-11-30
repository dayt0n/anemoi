from flask import Flask, abort, current_app, request

from anemoi.backends import init_backend
from anemoi.operator import ClientOperator
from anemoi.providers import Providers
from anemoi.util import anlog, get_my_public_ip, get_or_parse_yaml, record_type

app = Flask(__name__)


def setup_server(config_file):
    config = get_or_parse_yaml(config_file)
    app.config["anemoi.config"] = config

    # setup backend
    backend = init_backend(config)
    app.config["anemoi.backend"] = backend

    # setup providers
    providers = Providers(config_file=config)
    app.config["anemoi.providers"] = providers
    anlog.info("Starting anemoi...")
    return app


def get_ip():
    ip_addr = request.headers.get("cf-connecting-ip")
    if not ip_addr:
        ip_addr = request.access_route[-1]
    if ip_addr == "127.0.0.1":
        new_ip = get_my_public_ip()
        return new_ip if new_ip else ip_addr
    return ip_addr


@app.route("/")
def home():
    return "anemoi server"


@app.route("/check-in", methods=["POST", "GET"])
def check_in():
    if request.method == "POST":
        if not request.is_json:
            abort(400)
        data = dict(request.json)
    else:
        data = {
            "uuid": request.args.get("uuid"),
            "secret": request.args.get("secret"),
            "ip": request.args.get("ip"),
        }
    if not all(k in data for k in ("uuid", "secret")):
        abort(400)
    uuid = data.get("uuid")
    secret = data.get("secret")
    manually_set_ip = data.get("ip")
    co = ClientOperator(current_app.config.get("anemoi.backend"))
    res = co.validate_secret(uuid, secret)
    if not res:  # no auth, exit
        return "not changed", 200
    if client := co.backend.get_client(uuid=uuid):
        providers: Providers = current_app.config.get("anemoi.providers")
        provider = providers.get_provider(client.domain)
        ip = manually_set_ip or get_ip()
        rtype = record_type(ip)
        ips = provider.get_record_ips(client.domain)
        providers_ip_record = ""  # handle if IP changed on provider's side, then update it to the real one
        for i in ips:
            if rtype in i:  # noqa: SIM908
                providers_ip_record = i[rtype]
        if (
            co.did_ip_change(uuid, ip)
            or not providers_ip_record
            or (providers_ip_record and ip != providers_ip_record)
        ):
            co.update_ip(uuid, ip)
            if ip != providers_ip_record:
                if provider.update_record_ip(client.domain, ip, rtype=rtype):
                    msg = f"changed IP for {client.domain} to {ip}"
                else:
                    msg = f"error updating IP for {client.domain}"
            else:
                msg = f"updated IP for {client.domain} to {ip} in database"
            anlog.debug(msg)
            return msg, 200
    return "not changed", 200
