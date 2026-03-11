# Playground Runner

This directory contains a minimal Modal runner for the browser playground.

## Local development

Run the local HTTP endpoint from the repository root:

```bash
uv run python -m playground.local_runner --port 8787
```

That starts a local endpoint at `http://127.0.0.1:8787/run-skivvy` with permissive CORS so a local `nanoterm` dev server can call it from the browser.

## Local nanoterm demo

There is also a tiny browser app in `playground/web` that uses `nanoterm` as a library without modifying the nanoterm repo.

From `playground/web`:

```bash
npm install
npm run dev
```

`npm run dev` rebuilds the overlay automatically and starts the Vite dev server.

When developing locally, run the local runner yourself in another shell from the repository root:

```bash
uv run python -m playground.local_runner --port 8787
```

If you want the dev UI to talk to Modal instead, override the runner URL:

```bash
VITE_SKIVVY_RUNNER_URL=https://your-modal-endpoint.modal.run npm run dev
```

Open the Vite URL, and inside the terminal try:

```sh
pwd
ls
skivvy cfg.json
```

You can edit both the tests and the JSON API fixture files with `nano`, then rerun `skivvy cfg.json` to see the result.

For production-style builds, set the runner URL at build time:

```bash
VITE_SKIVVY_RUNNER_URL=https://your-modal-endpoint.modal.run npm run build
```

That same `VITE_SKIVVY_RUNNER_URL` can later come from a GitHub Actions variable or secret during deploy.

## Contract

The web endpoint accepts a JSON body with:

- `command`: non-empty string, executed with `sh -lc`
- `cwd`: working directory relative to the uploaded project root
- `files`: array of objects with `path` and `content`

The `files` array should contain the playground subtree snapshot, not the entire emulator filesystem.

Minimal payload shape:

```json
{
  "command": "skivvy cfg.json",
  "cwd": ".",
  "files": [
    {
      "path": "cfg.json",
      "content": "{\n  \"tests\": \"./tests\"\n}\n"
    }
  ]
}
```

In a real request, the array should also include the referenced test files and any static JSON files under `api/` that the local server should serve. For lightweight commands like `skivvy --version`, `files` can be an empty array.

## Execution model

- Each request creates a fresh temp workspace
- All uploaded project files are written into that workspace
- The built-in static JSON server is started against `api/`
- The uploaded `command` runs with `sh -lc` in the uploaded `cwd`
- The server process and workspace are removed before the request returns

## Modal settings

The runner is configured as a Restricted Function with:

- `restrict_modal_access=True`
- `block_network=True`

Warm container reuse is allowed on Modal, but each request still gets a fresh temp workspace and a fresh local static JSON server process.

If `block_network=True` prevents `skivvy` from reaching `127.0.0.1:8080`, that should be the first setting to revisit.

## Modal usage

Once you are happy with the local flow, the Modal wrapper uses the same request contract as the local runner in `playground/modal_runner.py:1`.

Typical next commands are:

```bash
modal serve playground/modal_runner.py
modal deploy playground/modal_runner.py
```

## GitHub Actions setup

Two workflows are included:

- `.github/workflows/playground-modal.yml` deploys the Modal runner
- `.github/workflows/playground-pages.yml` builds and deploys the browser app to GitHub Pages

Add these repository settings before enabling them:

- Repository secret `MODAL_TOKEN_ID`
- Repository secret `MODAL_TOKEN_SECRET`
- Repository variable `PLAYGROUND_RUNNER_URL`

`PLAYGROUND_RUNNER_URL` should be the public URL of the deployed Modal endpoint, and the Pages build passes it through as `VITE_SKIVVY_RUNNER_URL`.
