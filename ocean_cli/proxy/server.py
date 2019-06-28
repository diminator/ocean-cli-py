from flask import Flask, request, jsonify
from urllib import parse

from ocean_cli.ocean import get_ocean
from ocean_cli.proxy.services import (
    location_heatmap,
    gdrive
)

ocean = get_ocean('config.ini')

app = Flask(__name__)


def authorize(path,
              did=None,
              address=None,
              token=None,
              signed_token=None, **kwargs):
    try:
        if did and address and not ocean.check_permissions(did, address):
            print('error check_permissions')
            return False

        if token:
            secret = ocean.decrypt(did)[0]
            if not isinstance(secret, dict):
                print('error decrypt')
                return False

            if secret['url']['path'] != path:
                print('wrong path')
                return False

            qs = parse.parse_qs(secret['url']['qs'])
            # TODO: deep check on other query params as well
            if qs['token'][0] != token:
                print('wrong token')
                return False

        # TODO: deep check on other query params as well
        if signed_token and \
                (ocean.keeper.ec_recover(token, signed_token) != address.lower()):
            print('error sign')
            return False
    except KeyError as e:
        print('error', e)
        return False
    except ValueError as e:
        print('error', e)
        return False

    print(f'Access granted for {did} to {address} with {token}')
    return True


def handle(path):
    if path == 'docker/hello':
        import docker
        client = docker.from_env()
        response = client.containers.run("hello-world").decode()
        return jsonify(response)

    if path == 'locations/map':
        return location_heatmap.generate_map(**request.args)

    if path == 'locations/animation':
        return location_heatmap.generate_animation(**request.args)

    if path == 'gdrive/list':
        return jsonify(gdrive.list_files(**request.args))

    if path == 'gdrive/auth':
        return jsonify(gdrive.authorize(**request.args))

    return 'Not found', 404


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def proxy(path):
    if not authorize(path, **request.args):
        return f'No Access!\nREQ:{str(request.args)}', 402

    return handle(path)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
