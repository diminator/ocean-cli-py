from flask import Flask, request, jsonify

from squid_py.did import did_to_id_bytes

from ocean_cli.ocean import get_ocean
from ocean_cli.api.notebook import snippet_object

ocean = get_ocean('config.ini')

app = Flask(__name__)


def verify(did, address, token):
    grant_secret_store = False
    if did and address:
        grant_secret_store = ocean.keeper.\
            access_secret_store_condition.get_instance(). \
            check_permissions(did_to_id_bytes(did), address)

    print('secret store permission:', grant_secret_store)
    grant_token = False
    if token:
        # TODO check did.provider == me
        token_decrypted = ocean.decrypt(did)[0]['token'].split('&')[0]
        grant_token = token_decrypted == token

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
        return f'NO ACCESS! Order DID: {did}\n\n{snippet_object(did)}', 402

    print(f'ACCESS granted for {did} to {address} with {token}')
    if path == 'run':
        import docker
        client = docker.from_env()
        response = client.containers.run("hello-world").decode()

    if path == 'locationMap':
        from location_heatmap import generate_map
        latitude = request.args.get('latitude', 39.7)
        longitude = request.args.get('longitude', 3)
        zoom = request.args.get('zoom', 10)
        return generate_map(latitude, longitude, zoom)

    if path == 'locationAnimation':
        from location_heatmap import generate_animation
        epochs = request.args.get('epochs', 10)
        return generate_animation(epochs=int(epochs))

    print(response)
    return jsonify(response)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
