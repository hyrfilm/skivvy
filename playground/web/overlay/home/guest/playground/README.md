# Skivvy playground

Welcome — this browser playground is a small, sandbox-compatible subset of the full skivvy examples.

This directory is also exposed in the repository at `examples/dev_server`.

## Start here

```sh
pwd
ls
skivvy cfg.json
skivvy cfg_diffs.json
```

## Edit a test

```sh
nano tests/01_list_fortunes.json
skivvy cfg.json
```

## Edit the API response

```sh
nano api/fortunes/1.json
skivvy cfg.json
```

The `skivvy` command uploads this workspace, starts a tiny local JSON server in the sandbox, runs the command, and prints the output back in the terminal.

## Run it locally from the repo

```sh
cd examples/dev_server
uv run skivvy cfg.json
uv run skivvy cfg_diffs.json
```

If you want to start the tiny JSON server yourself:

```sh
cd examples/dev_server
python3 server.py 8080 api
```

Other skivvy example suites exist in the repository, but this playground only includes the self-contained files that are meant to run in the browser sandbox.
