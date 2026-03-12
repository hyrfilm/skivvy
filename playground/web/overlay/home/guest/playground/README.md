# Skivvy playground

Welcome — this browser playground is a self-contained sandbox where you can run and edit skivvy tests live.

This directory is also exposed in the repository at `examples/dev_server`.

## Quick start

```sh
ls
skivvy cfg.json
```

## Categories

Use the dropdown at the top of the page to switch between example sets, or run any config file directly:

| Config | What it covers |
|---|---|
| `cfg.json` | Basics — status codes, simple field checks |
| `cfg_diffs.json` | Failing tests with ndiff output |
| `cfg_diffs_unified.json` | Same failures, unified diff format |
| `cfg_diffs_table.json` | Same failures, side-by-side table format |
| `cfg_matchers.json` | All built-in matchers |
| `cfg_variables.json` | $store, $fetch, brace expansion, $write_file/$read_file |
| `cfg_oauth.json` | OAuth flow — POST login, capture token, use in header |
| `cfg_headers.json` | Sending request headers, asserting response headers |
| `cfg_graphql.json` | GraphQL-shaped responses, nested matching |

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

## Run it locally from the repo

```sh
cd examples/dev_server
uv run skivvy cfg.json
uv run skivvy cfg_matchers.json
uv run skivvy cfg_oauth.json
```

If you want to start the JSON server yourself:

```sh
cd examples/dev_server
python3 server.py 8080 api
```

The `skivvy` command uploads this workspace, starts the JSON server in the sandbox, runs the command, and streams the output back into the terminal.
