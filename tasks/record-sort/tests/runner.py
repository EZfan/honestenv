"""Call submitted programs as an unprivileged process and validate its response."""
import json
import subprocess
import sys

_APP_DIR = "/app"
_IDENTITY = {"user": 65534, "group": 65534, "extra_groups": []}

_WORKER = r'''
import contextlib, importlib, json, sys
request = json.load(sys.stdin)
def decode(value):
    tag, payload = value
    if tag == "tuple":
        return tuple(decode(item) for item in payload)
    if tag == "list":
        return [decode(item) for item in payload]
    if tag == "dict":
        return {key: decode(item) for key, item in payload.items()}
    return payload
def encode(value):
    if isinstance(value, tuple):
        return ["tuple", [encode(item) for item in value]]
    if isinstance(value, list):
        return ["list", [encode(item) for item in value]]
    if isinstance(value, dict):
        return ["dict", {key: encode(item) for key, item in value.items()}]
    return ["value", value]
request["args"] = decode(request["args"])
sys.path.insert(0, request["app"])
try:
    with contextlib.redirect_stdout(sys.stderr):
        function = getattr(importlib.import_module(request["module"]), request["function"])
        result = function(*request["args"])
    response = {"result": result, "args": encode(request["args"])}
except ValueError:
    response = {"error": "ValueError"}
print(json.dumps(response, allow_nan=False))
'''


def _encode(value):
    if isinstance(value, tuple):
        return ["tuple", [_encode(item) for item in value]]
    if isinstance(value, list):
        return ["list", [_encode(item) for item in value]]
    if isinstance(value, dict):
        return ["dict", {key: _encode(item) for key, item in value.items()}]
    return ["value", value]


def _decode(value):
    tag, payload = value
    if tag == "tuple":
        return tuple(_decode(item) for item in payload)
    if tag == "list":
        return [_decode(item) for item in payload]
    if tag == "dict":
        return {key: _decode(item) for key, item in payload.items()}
    if tag != "value":
        raise ValueError("invalid response type")
    return payload


def call(module, function):
    def invoke(*args):
        process = subprocess.run(
            [sys.executable, '-I', '-c', _WORKER],
            input=json.dumps({'module': module, 'function': function, 'args': _encode(args), 'app': _APP_DIR}),
            text=True, capture_output=True, timeout=5,
            cwd='/', **_IDENTITY,
        )
        if process.returncode != 0:
            raise AssertionError(f'submission terminated: {process.returncode}')
        try:
            response = json.loads(process.stdout)
            if response.get('error') == 'ValueError':
                raise ValueError('submission raised ValueError')
            result, after = response['result'], _decode(response['args'])
        except (json.JSONDecodeError, KeyError, TypeError, IndexError) as error:
            raise AssertionError('missing or invalid submission response') from error
        for before, value in zip(args, after):
            if isinstance(before, list) and isinstance(value, list):
                before[:] = value
            elif isinstance(before, dict) and isinstance(value, dict):
                before.clear()
                before.update(value)
        return result
    return invoke


def run_binary(args):
    return subprocess.run(args, text=True, capture_output=True, timeout=5,
                          cwd='/', **_IDENTITY)
