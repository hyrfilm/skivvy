from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path, PurePosixPath


SERVER_HOST = "127.0.0.1"
SERVER_PORT = 8080
SERVER_IDLE_TIMEOUT_SECONDS = 60
SERVER_STARTUP_TIMEOUT_SECONDS = 3.0
RUN_TIMEOUT_SECONDS = 25
DEFAULT_SERVER_SCRIPT = Path(__file__).resolve().parent.parent / "examples" / "dev_server" / "server.py"
PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROJECT_SRC = Path(__file__).resolve().parent.parent / "src"


def _validate_relative_path(raw_path: str) -> str:
    if not isinstance(raw_path, str) or not raw_path:
        raise ValueError("each file path must be a non-empty string")

    normalized = raw_path.replace("\\", "/")
    path = PurePosixPath(normalized)

    if path.is_absolute():
        raise ValueError(f"absolute paths are not allowed: {raw_path}")
    if any(part in ("", ".", "..") for part in path.parts):
        raise ValueError(f"invalid path: {raw_path}")

    return str(path)


def _write_workspace(files: list[dict], workspace_dir: Path) -> None:
    for entry in files:
        if not isinstance(entry, dict):
            raise ValueError("each file entry must be an object")

        raw_path = entry.get("path")
        content = entry.get("content")
        if not isinstance(content, str):
            raise ValueError(f"file content for {raw_path!r} must be a string")

        relative_path = _validate_relative_path(raw_path)
        target = workspace_dir / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)


def _validate_cwd(raw_cwd: str) -> str:
    if raw_cwd in ("", "."):
        return "."
    return _validate_relative_path(raw_cwd)


def _wait_for_server(host: str, port: int, timeout_seconds: float) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            try:
                sock.connect((host, port))
                return True
            except OSError:
                time.sleep(0.05)
    return False


def _start_server(workspace_dir: Path, server_script: Path) -> subprocess.Popen:
    api_root = workspace_dir / "api"
    if not api_root.is_dir():
        legacy_api_root = workspace_dir / "examples" / "dev_server" / "api"
        if legacy_api_root.is_dir():
            api_root = legacy_api_root
        else:
            raise ValueError("workspace must include api or examples/dev_server/api")
    if not server_script.is_file():
        raise ValueError(f"server script not found: {server_script}")

    server = subprocess.Popen(
        [
            sys.executable,
            str(server_script),
            str(SERVER_PORT),
            str(api_root),
            str(SERVER_IDLE_TIMEOUT_SECONDS),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    if _wait_for_server(SERVER_HOST, SERVER_PORT, SERVER_STARTUP_TIMEOUT_SECONDS):
        return server

    startup_output = ""
    if server.poll() is not None:
        startup_output, _ = server.communicate(timeout=1)
    else:
        server.terminate()
        try:
            startup_output, _ = server.communicate(timeout=1)
        except subprocess.TimeoutExpired:
            server.kill()
            startup_output, _ = server.communicate(timeout=1)

    message = "local server failed to start"
    if startup_output.strip():
        message = f"{message}: {startup_output.strip()}"
    raise RuntimeError(message)


def _should_start_server(workspace_dir: Path) -> bool:
    return (workspace_dir / "api").is_dir() or (workspace_dir / "examples" / "dev_server" / "api").is_dir()


def _stop_server(server: subprocess.Popen | None) -> None:
    if server is None:
        return
    if server.poll() is not None:
        try:
            server.communicate(timeout=1)
        except subprocess.TimeoutExpired:
            server.kill()
        return

    server.terminate()
    try:
        server.communicate(timeout=1)
    except subprocess.TimeoutExpired:
        server.kill()
        server.communicate(timeout=1)


def _run_command(command_text: str, cwd: str, workspace_dir: Path) -> tuple[str, int]:
    shell_command = ["sh", "-lc", command_text]
    if PROJECT_SRC.is_dir() and shutil.which("uv"):
        command = ["uv", "run", "--project", str(PROJECT_ROOT), *shell_command]
    else:
        command = shell_command

    pythonpath_parts = []
    if PROJECT_SRC.is_dir():
        pythonpath_parts.append(str(PROJECT_SRC))
    existing_pythonpath = os.environ.get("PYTHONPATH")
    if existing_pythonpath:
        pythonpath_parts.append(existing_pythonpath)

    completed = subprocess.run(
        command,
        cwd=workspace_dir / cwd if cwd != "." else workspace_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=RUN_TIMEOUT_SECONDS,
        env={
            **os.environ,
            "TERM": "xterm-256color",
            "COLORTERM": "truecolor",
            "FORCE_COLOR": "1",
            "COLUMNS": "120",
            **({"PYTHONPATH": os.pathsep.join(pythonpath_parts)} if pythonpath_parts else {}),
        },
    )
    return completed.stdout, completed.returncode


def run_request(body: dict, server_script: Path | None = None) -> dict:
    started_at = time.monotonic()
    workspace_dir = Path(tempfile.mkdtemp(prefix="skivvy-playground-"))
    server: subprocess.Popen | None = None

    try:
        command_text = body.get("command", "")
        cwd = body.get("cwd", ".")
        files = body.get("files", [])

        if not isinstance(command_text, str) or not command_text.strip():
            return {
                "output": "request body must include a non-empty string field named 'command'\n",
                "exitCode": 2,
                "durationMs": int((time.monotonic() - started_at) * 1000),
            }
        if not isinstance(files, list):
            return {
                "output": "request body must include an array field named 'files'\n",
                "exitCode": 2,
                "durationMs": int((time.monotonic() - started_at) * 1000),
            }

        validated_cwd = _validate_cwd(cwd)
        _write_workspace(files, workspace_dir)
        working_dir = workspace_dir / validated_cwd if validated_cwd != "." else workspace_dir
        if not working_dir.is_dir():
            return {
                "output": f"request cwd does not exist: {cwd}\n",
                "exitCode": 2,
                "durationMs": int((time.monotonic() - started_at) * 1000),
            }
        if _should_start_server(workspace_dir):
            server = _start_server(workspace_dir, server_script or DEFAULT_SERVER_SCRIPT)
        output, exit_code = _run_command(command_text, validated_cwd, workspace_dir)
        return {
            "output": output,
            "exitCode": exit_code,
            "durationMs": int((time.monotonic() - started_at) * 1000),
        }
    except subprocess.TimeoutExpired:
        return {
            "output": f"skivvy timed out after {RUN_TIMEOUT_SECONDS} seconds\n",
            "exitCode": 124,
            "durationMs": int((time.monotonic() - started_at) * 1000),
        }
    except Exception as exc:
        return {
            "output": f"runner error: {exc}\n",
            "exitCode": 1,
            "durationMs": int((time.monotonic() - started_at) * 1000),
        }
    finally:
        _stop_server(server)
        shutil.rmtree(workspace_dir, ignore_errors=True)
