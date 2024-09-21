# anemoi

Anemoi is a least privilege dynamic DNS server. See [the blog post](https://dayt0n.com/articles/anemoi) for more info.

### Installation
For production systems, install with:
```bash
pip install anemoi-dns
```

For development purposes, clone and install locally:
```bash
git clone https://github.com/dayt0n/anemoi && cd anemoi
pip install -e .
```

## Usage

### Configuration
Domains and backends are specified with a YAML configuration file. An example config file is provided at [example_config.yml](https://github.com/dayt0n/anemoi/tree/main/example_config.yml).

#### Domains
You can have multiple domains on one Anemoi instance. To do this, create a `config.yml` file that looks something like this:
```yaml
domains:
  - zone: random-domain.org
    provider: cloudflare
    token: AAAAAAAAAAAAAAAAAAAAAAAAAAA

  - zone: mydomain.com
    provider: cloudflare
    email: admin-user@yourdomain.com
    key: asfdasfdasddfasddfasdfasdf

  - zone: website.com
    provider: porkbun
    apikey: pk1_asdfasdfasdfasdfadsf
    secret: sk1_lkjhlkjhlkjhlkjhlkjh
```

The `provider` field can be any of:
- `cloudflare`
  - takes: `token` OR `email` + `key`
- `porkbun`
  - takes: `apikey` + `secret`

#### Backend
A backend must be specified in the config file like:
```yaml
backend:
  type: database
  vendor: sqlite
  path: /home/me/my-sqlite.db
```

`type` can be one of:
- `tinydb`
- `database`

`vendor` is only necessary for `database` (for now) and can be one of:
- `sqlite`
- `postgres`

`path` is either a file path or full database connection URL.

### Running the server in development
All commands require you to use a `-c /path/to/config.yml` unless you want to use the default config path.

```bash
anemoi -c /path/to/config.yml -v server
```

### Running the server in production
You can use gunicorn to run the server after installing Anemoi:
```bash
gunicorn -b 0.0.0.0:80 'anemoi.server:setup_server("/path/to/config.yml")'
```

### Creating a new client
To create a new client, run:
```bash
anemoi -c /path/to/config.yml client add -d yoursub.domain.com
```

This will give you a UUID and secret to use.

### Deleting a client
If you believe a client has been compromised, you can revoke its access by deleting it.

To delete a client, run:
```bash
anemoi client delete -d yoursub.domain.com
```

### Listing current clients
To see a list of current registered clients, run:
```bash
anemoi client list
```

### Running a client

A client is just a fancy word for a single web request. The request must contain a JSON `uuid` and `secret` field, and that's it. It can be done using a `curl` command:
```bash
curl -X POST http://an.anemoi-server.com:9999/check-in -H 'Content-Type: application/json' \
-d '{"uuid":"aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "secret":"averylongsecrethere"}'
```

## Development
Before adding any pull requests, make sure you have [`pre-commit`](https://pre-commit.com/) installed, then add the hooks for this repo:
```bash
pre-commit install
```

Anemoi allows you to have multiple DNS provider types as well as backend types to store your client data.

### Providers
Adding a new DNS provider should be fairly simple.

Let's say there is a DNS provider, like Cloudflare, called `Groundwater`. To add Groundwater as a dynamic DNS provider, do the following:
1. Create a file called [`anemoi/providers/groundwater.py`](https://github.com/dayt0n/anemoi/tree/main/anemoi/providers/groundwater.py).
2. Add a class in that file called `GroundwaterProvider(Provider)`. The class should have a skeleton like:
```python
class GroundwaterProvider(Provider):
    key: str = ""
    def __init__(self, config):
      # parse config to get Groundwater API keys and such, return None on failure
      if key := config.get("key"):
          self.key = key
      else:
          return None

    # returns list of {'A': '1.1.1.1'} objects
    def get_record_ips(self, subdomain) -> List[Dict[str, str]]:
        # query API here, then return the records as a dictionary
        result = requests.get(f"https://groundwater.dev/api/get_records/{subdomain}").json()["records"]
        """
        imagine the result looks like:
        [
            {
                "domain":"test.groundwater-test.dev",
                "type": "A",
                "ip": "1.1.1.1",
                "ttl": 600,
            }
        ]
        """
        return [{x['type']: x['ip']} for x in records]

    # returns bool of if the update succeeded or not
    def update_record_ip(self, subdomain: str, ip, rtype="A") -> bool:
        if not is_ip_record_valid(ip, rtype):
            return False
        # parse out domain name, then update the IP with the record type rtype
        #   on the Groundwater API here
        records = requests.get(f"https://groundwater.dev/api/get_records/{subdomain}").json()["records"]
        if not records:
            # create new record
            result = requests.post(f"https://groundwater.dev/api/create_record/{subdomain}/{rtype}/{ip}").json()
            if result.get("status") == "success":
                return True
            return False
        # update existing record
        for record in records:
            if ip == record["ip"]:
                # don't update record if not necessary
                continue
            result = requests.post(f"https://groundwater.dev/api/update_record/{subdomain}/{rtype}/{ip}").json()
            if result.get("status") != "success":
                return False
        return True
```
3. Use your provider in the config:
```yaml
domains:
  - zone: groundwater-test.com
    key: asdfasdflkjhlkjh
    provider: groundwater
```

### Backends

All data storage backends must inherit the `Backend` class. The skeleton of the backend should implement the following methods:
```python
class YourBackend(Backend):

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
```

[`anemoi.backends.database`](https://github.com/dayt0n/anemoi/tree/main/anemoi/backends/database.py) and [`anemoi.backends.tinydb`](https://github.com/dayt0n/anemoi/tree/main/anemoi/backends/tinydb.py) may be useful to look at as you are creating your new data storage backend.
