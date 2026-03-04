# Dev Server Example

This example runs skivvy against a tiny local static JSON API server.

## Start the server

From repository root:

```bash
python3 examples/dev_server/server.py 8080 examples/dev_server/api
```

Server behavior:
- Binds to `127.0.0.1`.
- Uses `/tmp/skivvy_dev_server.pid` as a lock (single-server intent).
- Auto-shuts down after idle time (default `60` seconds).
- Route mapping:
  - `/fortunes` -> `fortunes.json` or `fortunes/index.json`
  - `/fortunes/1` -> `fortunes/1.json`

You can override idle timeout:

```bash
python3 examples/dev_server/server.py 8080 examples/dev_server/api 300
```

Stop explicitly:

```bash
python3 examples/dev_server/server.py stop
```

## Run passing suites

These tests use full URLs (no `base_url` needed):

```bash
uv run skivvy examples/dev_server/cfg.json
```

## Run intentional failures to inspect diffs

```bash
uv run skivvy examples/dev_server/cfg_diffs.json
```

Try alternate diff styles with `--set`:

```bash
uv run skivvy examples/dev_server/cfg_diffs.json --set diff_ndiff=false --set diff_unified=true
uv run skivvy examples/dev_server/cfg_diffs.json --set diff_ndiff=false --set diff_table=true
uv run skivvy examples/dev_server/cfg_diffs.json --set diff_full=true
```
