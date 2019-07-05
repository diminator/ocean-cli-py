from flask import Flask, request, jsonify
from flask_cors import CORS
from urllib import parse

from ocean_cli.ocean import get_ocean
from ocean_cli.proxy.services import (
    location_heatmap,
    gdrive
)

ocean = get_ocean('config.ini')

app = Flask(__name__)
CORS(app)


def authorize(did=None,
              consumerAddress=None,
              agreementId=None,
              agreementIdSignature=None, **kwargs):

    if not (did and consumerAddress) \
            or not ocean.check_permissions(did, consumerAddress)\
            or not (agreementId and agreementIdSignature)\
            or not (ocean.keeper.ec_recover(agreementId, agreementIdSignature)
                    == consumerAddress.lower()):
        raise ValueError('error check_permissions')

    secret = ocean.decrypt(did)[0]
    if not isinstance(secret, dict):
        raise ValueError('could not decrypt')

    print(f'Access granted for {did} to {consumerAddress} with {agreementId}')
    return \
        secret['url']['path'], \
        {k: v[0] for k, v in parse.parse_qs(secret['url']['qs']).items()}


def handle(path, qs):
    if path == 'docker/hello':
        import docker
        client = docker.from_env()
        response = client.containers.run("hello-world").decode()
        return jsonify(response)

    if path == 'locations/map':
        return location_heatmap.generate_map(**qs)

    if path == 'locations/animation':
        return location_heatmap.generate_animation(**qs)

    if path == 'gdrive/list':
        return jsonify(gdrive.list_files(**qs))

    if path == 'gdrive/auth':
        return jsonify(gdrive.authorize(**qs))

    return 'Not found', 404


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def proxy(path):
    try:
        return handle(*authorize(**request.args))
    except (KeyError, ValueError) as e:
        print(e)
        return f'No Access!\nREQUEST:{str(request.args)}', 402


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
