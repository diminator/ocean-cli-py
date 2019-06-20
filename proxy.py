from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def proxy(path):
    return jsonify({
        'path': path,
        'method': request.method,
        'args': request.args
    })


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
