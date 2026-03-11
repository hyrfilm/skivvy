"""Minimal Modal wrapper for the skivvy playground runner."""

from pathlib import Path

import modal

from playground.runner_core import run_request


APP_NAME = "skivvy-playground-runner"
PLAYGROUND_ROOT = Path(__file__).resolve().parent.parent
SERVER_SCRIPT = PLAYGROUND_ROOT / "examples" / "dev_server" / "server.py"
REMOTE_SERVER_SCRIPT = "/opt/skivvy-playground/server.py"

image = (
    modal.Image.from_registry("python:3.13-alpine")
    .pip_install("skivvy", "fastapi[standard]")
    .add_local_python_source("playground", "modal_runner", copy=True)
    .add_local_file(str(SERVER_SCRIPT), remote_path=REMOTE_SERVER_SCRIPT, copy=True)
)

app = modal.App(APP_NAME, image=image, include_source=False)


@app.function(
    restrict_modal_access=True,
    block_network=True,
    timeout=40,
)
@modal.fastapi_endpoint(method="POST")
def run_skivvy(body: dict) -> dict:
    return run_request(body, server_script=Path(REMOTE_SERVER_SCRIPT))
