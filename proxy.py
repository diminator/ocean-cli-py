from flask import Flask, request, jsonify
from ocean_cli.api.assets import decrypt

from squid_py.config import Config
from squid_py.did import did_to_id_bytes
from squid_py.ocean.ocean import Ocean
from ocean_cli.ocean import get_default_account

config = Config(filename='./config.ini')
ocean = Ocean(config)
account = get_default_account(config)

app = Flask(__name__)


def verify(did, address, token):
    grant_secret_store = False
    if did and address:
        grant_secret_store = ocean.keeper.\
            access_secret_store_condition.get_instance(). \
            check_permissions(did_to_id_bytes(did), address)

    grant_token = False
    if token:
        # TODO check did.provider == me
        grant_token = decrypt(ocean, account, did)[0]['token'] == token

    return grant_secret_store and grant_token


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def proxy(path):
    response = {
        'path': path,
        'method': request.method,
        'args': request.args
    }

    did = request.args.get('did', None)
    address = request.args.get('address', None)
    token = request.args.get('token', None)

    if not did or not verify(did, address, token):
        return f'NO ACCESS! First order DID: {did}', 402

    if path == 'run':
        import docker
        client = docker.from_env()
        response = client.containers.run("hello-world").decode()

    print(response)
    return jsonify(response)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
