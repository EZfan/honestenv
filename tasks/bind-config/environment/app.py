from pathlib import Path
import tomllib


def load_settings():
    with Path('/app/config.toml').open('rb') as config:
        settings = tomllib.load(config)
    return settings['host'], settings['port'], settings['workers']


def bind_address():
    host, port, _ = load_settings()
    return f'{host}:{port}'
