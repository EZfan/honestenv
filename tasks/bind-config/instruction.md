# Repair bind configuration

Fix only `/app/config.toml`. Do not modify `/app/app.py`, which is already
correct. The application reads the TOML configuration and exposes
`load_settings()`, returning `(host, port, workers)`, and `bind_address()`,
returning `"host:port"`.

Set host to `"127.0.0.1"`, port to the integer `8000`, and workers to the
integer `2`. Leave the corrected configuration at `/app/config.toml`. Use only
the Python standard library.
