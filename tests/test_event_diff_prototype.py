import json
import sys

import pytest

from skivvy import events
from skivvy.skivvy import run
from skivvy.util.str_util import pretty_diff, tojsonstr

FAKE_SERVER = "localhost"
FAKE_PORT = 8888


@pytest.fixture(scope="session")
def httpserver_listen_address():
    return (FAKE_SERVER, FAKE_PORT)


def _write_json(path, data):
    path.write_text(json.dumps(data))
    return path


def _run_cli_with_cfg(cfg_file, *args):
    old_argv = sys.argv
    try:
        sys.argv = ["skivvy", str(cfg_file), *args]
        return run()
    finally:
        sys.argv = old_argv


def test_failed_event_payload_can_drive_diff_rendering(httpserver, tmp_path):
    httpserver.expect_request("/api/diff").respond_with_json({"ok": False})

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    _write_json(
        tests_dir / "01_fail.json",
        {
            "url": "/api/diff",
            "status": 200,
            "response": {"ok": True},
        },
    )
    cfg_file = _write_json(
        tmp_path / "cfg.json",
        {
            "tests": str(tests_dir),
            "ext": ".json",
            "base_url": httpserver.url_for("/").rstrip("/"),
            "log_level": "ERROR",
            "file_order": "lexical",
        },
    )

    captured = {}

    def on_failed(_sender, **payload):
        captured["payload"] = payload
        captured["diff"] = pretty_diff(
            tojsonstr(payload["expected"]),
            tojsonstr(payload["actual"]),
            diff_type="unified",
        )

    sig = events.signal(events.TEST_FAILED)
    sig.connect(on_failed)
    try:
        result = _run_cli_with_cfg(cfg_file, "-t")
    finally:
        sig.disconnect(on_failed)

    assert result is False
    payload = captured["payload"]
    assert payload["event"] == events.TEST_FAILED
    assert payload["testfile"].endswith("01_fail.json")
    assert payload["expected"]["response"] == {"ok": True}
    assert payload["actual"]["response"] == {"ok": False}
    assert "error_context" in payload
    assert "Traceback" in payload["exception"]

    diff = captured["diff"]
    assert "[red]-" in diff
    assert "[green]+" in diff
    assert '"ok": true' in diff
    assert '"ok": false' in diff


def test_verify_mismatch_emits_phase_failed_before_test_failed(httpserver, tmp_path):
    httpserver.expect_request("/api/phase").respond_with_json({"ok": False})

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    _write_json(
        tests_dir / "01_phase_fail.json",
        {
            "url": "/api/phase",
            "status": 200,
            "response": {"ok": True},
        },
    )
    cfg_file = _write_json(
        tmp_path / "cfg.json",
        {
            "tests": str(tests_dir),
            "ext": ".json",
            "base_url": httpserver.url_for("/").rstrip("/"),
            "log_level": "ERROR",
            "file_order": "lexical",
        },
    )

    seen = []

    def on_phase_failed(_sender, **payload):
        seen.append(("phase_failed", payload["phase"], payload.get("testfile")))

    def on_test_failed(_sender, **payload):
        seen.append(("test_failed", payload["testfile"]))

    phase_sig = events.signal(events.TEST_PHASE_FAILED)
    test_sig = events.signal(events.TEST_FAILED)
    phase_sig.connect(on_phase_failed)
    test_sig.connect(on_test_failed)
    try:
        result = _run_cli_with_cfg(cfg_file, "-t")
    finally:
        phase_sig.disconnect(on_phase_failed)
        test_sig.disconnect(on_test_failed)

    assert result is False
    assert ("phase_failed", "verify_response", str(tests_dir / "01_phase_fail.json")) in seen
    phase_idx = next(i for i, item in enumerate(seen) if item[0] == "phase_failed")
    fail_idx = next(i for i, item in enumerate(seen) if item[0] == "test_failed")
    assert phase_idx < fail_idx
