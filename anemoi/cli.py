import click
from jsonschema import ValidationError

from anemoi.backends import init_backend
from anemoi.operator import ClientOperator
from anemoi.server import setup_server
from anemoi.util import get_or_parse_yaml, set_loglevel


# walk up the ctx parent chain until you run into the desired parameter
def find_ctx_param(ctx, param: str):
    ctx_copy = ctx
    while True:
        if val := ctx_copy.params.get(param):
            return val
        ctx_copy = ctx_copy.parent


def get_config(ctx):
    config_file = find_ctx_param(ctx, "config")
    try:
        config = get_or_parse_yaml(config_file)
    except ValidationError as e:
        ctx.fail(f"Config file validation failed on {config_file}:\n{e}")
    return config


@click.group()
@click.option("-v", is_flag=True)
@click.option(
    "-c",
    "--config",
    help="Anemoi configuration file",
    default="~/.anemoi/config.yml",
    type=click.Path(exists=True),
)
@click.version_option(package_name="anemoi-dns")
def cli(v, config):
    set_loglevel(v)


@cli.command()
@click.option("-s", "--serve-host", help="IP/URL to serve anemoi", default="127.0.0.1")
@click.option("-p", "--port", help="port for server", default=9999)
@click.pass_context
def server(ctx, serve_host, port):
    app = setup_server(get_config(ctx))
    app.run(host=serve_host, port=port)


@cli.group()
def client():
    pass


@client.command(help="add new client")
@click.option("-d", "--domain", help="domain to update for this client", prompt=True)
@click.option("-i", "--ip", help="optional known starting IP")
@click.pass_context
def add(ctx, domain, ip):
    config = get_config(ctx)
    backend = init_backend(config)
    co = ClientOperator(backend)
    if not ip:
        ip = ""
    zones = [x.get("zone") for x in config.get("domains")]
    for zone in zones:
        if domain.endswith(zone):
            break
    else:
        ctx.fail(f"No zone defined for {domain}")
    client, secret = co.new_client(domain, ip)
    click.echo("\n- Client info -")
    click.echo(f"uuid: {client.uuid}")
    click.echo(f"secret: {secret}")


@client.command(help="list all clients")
@click.pass_context
def list(ctx):
    backend = init_backend(get_config(ctx))
    co = ClientOperator(backend)
    if len(co.clients) == 0:
        click.echo("No clients found")
        exit(0)
    click.echo("Clients:")
    for client in co.clients:
        click.echo(f" - {client.uuid} ({client.domain})")


@client.command(help="delete clients")
@click.option("-d", "--domain", help="domain of client to delete")
@click.option("-u", "--uuid", help="UUID of client to delete")
@click.pass_context
def delete(ctx, domain, uuid):
    if (not domain and not uuid) or (uuid and domain):
        ctx.fail("Specify one of 'uuid' or 'domain'.")
    backend = init_backend(get_config(ctx))
    co = ClientOperator(backend)
    if domain:
        res = co.delete_client(domain=domain)
    elif uuid:
        res = co.delete_client(uuid=uuid)
    if res:
        click.echo(f"Deleted client: {res}")
    else:
        click.echo("No matching clients found")


if __name__ == "__main__":
    cli()
