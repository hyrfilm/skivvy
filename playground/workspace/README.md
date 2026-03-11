# Skivvy playground

Welcome — this browser playground is a small, sandbox-compatible subset of the full skivvy examples.

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

Other skivvy example suites exist in the repository, but this playground only includes the self-contained files that are meant to run in the browser sandbox.
