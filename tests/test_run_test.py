import logging
import os
import pprint
import json
import pytest
import sys
from werkzeug.wrappers import Response

from skivvy import events
from skivvy.skivvy import run_test, run, STATUS_OK, STATUS_FAILED
from skivvy.skivvy_config2 import Option, Settings, create_test_config
from skivvy.test_runner import create_request
from skivvy.util import file_util, log, str_util

FAKE_SERVER = "localhost"
FAKE_PORT = 8888


@pytest.fixture
def my_httpserver(request, httpserver):
    request.cls.httpserver = httpserver


default_cfg = {"base_url": f"http://{FAKE_SERVER}:{FAKE_PORT}", "log_level": "DEBUG"}


@pytest.fixture(scope="session")
def httpserver_listen_address():
    return (FAKE_SERVER, FAKE_PORT)


def write_json_file(filename, data):
    filename.write_text(json.dumps(data))
    return filename


def run_cli_with_args(cfg_file, *args):
    old_argv = sys.argv
    try:
        sys.argv = ["skivvy", str(cfg_file), *args]
        return run()
    finally:
        sys.argv = old_argv


def clear_tmp_file_registry():
    # file_util tracks temp files globally across tests; clear it to keep run() cleanup isolated
    file_util._tmp_files.clear()


def test_fortune_01_successful(httpserver):
    httpserver.expect_request("/api/fortune/1").respond_with_json(
        {"wisdom": "If it seems that fates are aginst you today, they probably are."}
    )
    status, error_context = run_test(
        "./tests/fixtures/testcases/check_status.json", default_cfg
    )
    assert status is STATUS_OK
    assert error_context is None


def test_fortune_01_failing(httpserver):
    # lowercase i should make it fail since it's doing an exact match
    httpserver.expect_request("/api/fortune/1").respond_with_json(
        {"wisdom": "If it seems that fates are aginst you today, they probably are."}
    )
    status, error_context = run_test(
        "./tests/fixtures/testcases/check_exact_match.json", default_cfg
    )
    assert status is STATUS_FAILED
    assert "if it seems" in error_context.get("expected").get("response").get("wisdom")
    assert "If it seems" in error_context.get("actual").get("response").get("wisdom")


def test_fortune_02_match_subsets(httpserver):
    httpserver.expect_request("/api/fortune").respond_with_json(
        {"wisdom": "You only live once."}
    )
    status, error_context = run_test(
        "./tests/fixtures/testcases/match_subset.json", default_cfg
    )
    assert status is STATUS_OK
    # assert error_context is None


def test_match_subsets_missing_key_fails_by_default(httpserver):
    # Some entries lack the 'score' key entirely; with match_subsets, this should
    # fail by default unless skip_empty_objects is enabled AND they are empty objects.
    httpserver.expect_request("/api/items").respond_with_json(
        {"items": [{"name": "Alice", "score": 42}, {"name": "Bob"}]}
    )
    status, error_context = run_test(
        "./tests/fixtures/testcases/match_subset_missing_key.json", default_cfg
    )
    assert status is STATUS_FAILED
    assert error_context is not None


def test_match_subsets_empty_object_can_be_skipped(httpserver):
    httpserver.expect_request("/api/items").respond_with_json(
        {"items": [{"score": 42}, {}]}
    )
    status, error_context = run_test(
        "./tests/fixtures/testcases/match_subset_empty_object_skip.json",
        default_cfg,
    )
    assert status is STATUS_OK
    assert error_context is None


def test_brace_expansion_warnings_non_strict_returns_unexpanded_url():
    testcase = create_test_config({
        "base_url": f"http://{FAKE_SERVER}:{FAKE_PORT}",
        "url": "<undefined_brace_expansion_var>/api/data",
        "method": "get",
        "brace_expansion": True,
        "brace_expansion_warnings": True,
        "brace_expansion_strict": False,
    })
    request, _ = create_request(testcase)
    assert "<undefined_brace_expansion_var>" in request["url"]


def test_brace_expansion_strict_raises_on_undefined_variable():
    testcase = create_test_config({
        "base_url": f"http://{FAKE_SERVER}:{FAKE_PORT}",
        "url": "<undefined_brace_expansion_var>/api/data",
        "method": "get",
        "brace_expansion": True,
        "brace_expansion_warnings": False,
        "brace_expansion_strict": True,
    })
    with pytest.raises(ValueError):
        create_request(testcase)


def test_run_test_supports_brace_expansion_from_environment(httpserver, tmp_path, monkeypatch):
    monkeypatch.setenv("USER_ID", "123")
    httpserver.expect_request("/api/123").respond_with_json({"ok": True})

    testcase = {
        "url": "/api/<env.USER_ID>",
        "method": "get",
        "status": 200,
        "brace_expansion": True,
    }
    testcase_file = tmp_path / "env_brace_expansion.json"
    testcase_file.write_text(json.dumps(testcase))

    status, error_context = run_test(str(testcase_file), default_cfg)
    assert status is STATUS_OK
    assert error_context is None


def test_matcher_options_valid_url_protocol_relative(httpserver):
    # API returns a protocol-relative URL; matcher_options expands it to http:// before validating
    httpserver.expect_request("/api/photo").respond_with_json(
        {"url": f"//{FAKE_SERVER}:{FAKE_PORT}/image.png"}
    )
    httpserver.expect_request("/image.png").respond_with_data(b"", status=200)
    status, error_context = run_test(
        "./tests/fixtures/testcases/matcher_options_valid_url.json",
        {
            **default_cfg,
            "matcher_options": {
                "$valid_url": {"replace": {"^//": "http://"}}
            },
        },
    )
    assert status is STATUS_OK
    assert error_context is None


def test_run_loads_and_uses_custom_matcher_from_matchers_directory(httpserver, tmp_path):
    httpserver.expect_request("/api/custom-matcher").respond_with_json({"n": 4})

    matchers_dir = tmp_path / "matchers"
    matchers_dir.mkdir()
    (matchers_dir / "is_even.py").write_text(
        "def match(expected, actual):\n"
        "    return (isinstance(actual, int) and actual % 2 == 0, 'expected an even integer')\n"
    )

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    write_json_file(
        tests_dir / "01_custom_matcher.json",
        {
            "url": "/api/custom-matcher",
            "status": 200,
            "response": {"n": "$is_even"},
        },
    )
    cfg_file = write_json_file(
        tmp_path / "cfg.json",
        {
            "tests": str(tests_dir),
            "ext": ".json",
            "matchers": str(matchers_dir),
            "base_url": f"http://{FAKE_SERVER}:{FAKE_PORT}",
            "log_level": "ERROR",
            "file_order": "lexical",
        },
    )

    assert run_cli_with_args(cfg_file, "-t") is True


def test_cli_overrides_take_precedence_over_test_file(httpserver, tmp_path):
    httpserver.expect_request("/api/fortune/1").respond_with_json(
        {"wisdom": "If it seems that fates are aginst you today, they probably are."}
    )

    testcase = {
        "url": "/api/fortune/1",
        "method": "get",
        "status": 200,
        "log_level": "DEBUG",
    }
    testcase_file = tmp_path / "test.json"
    testcase_file.write_text(json.dumps(testcase))

    logger = logging.getLogger("skivvy.util.log")
    original_level = logger.level
    try:
        status, error_context = run_test(
            str(testcase_file),
            default_cfg,
            cli_overrides={"log_level": "ERROR"},
        )
        assert status is STATUS_OK
        assert error_context is None
        assert logger.level == logging.ERROR
    finally:
        logger.setLevel(original_level)


def test_run_without_include_filters_does_not_crash(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "01.json").write_text(
        json.dumps({"url": "/api/fortune/1", "status": 200, "response": {}})
    )

    cfg = {
        "tests": str(tests_dir),
        "ext": ".json",
        "base_url": "http://127.0.0.1:1",
        "log_level": "ERROR",
        "fail_fast": True,
    }
    cfg_file = tmp_path / "cfg.json"
    cfg_file.write_text(json.dumps(cfg))

    old_argv = sys.argv
    try:
        sys.argv = ["skivvy", str(cfg_file), "-t"]
        result = run()
    finally:
        sys.argv = old_argv

    assert result is False


def test_run_test_verifies_response_headers_case_insensitively(httpserver, tmp_path):
    httpserver.expect_request("/api/headers").respond_with_json(
        {"ok": True},
        headers={"x-trace-id": "trace-123"},
    )
    testcase_file = write_json_file(
        tmp_path / "response_headers_ok.json",
        {
            "url": "/api/headers",
            "method": "get",
            "status": 200,
            "response_headers": {"X-Trace-Id": "trace-123"},
        },
    )

    status, error_context = run_test(str(testcase_file), default_cfg)

    assert status is STATUS_OK
    assert error_context is None


def test_run_test_response_headers_mismatch_populates_error_context(httpserver, tmp_path):
    httpserver.expect_request("/api/headers-mismatch").respond_with_json(
        {"ok": True},
        headers={"x-trace-id": "actual-trace"},
    )
    testcase_file = write_json_file(
        tmp_path / "response_headers_fail.json",
        {
            "url": "/api/headers-mismatch",
            "method": "get",
            "status": 200,
            "response_headers": {"X-Trace-Id": "expected-trace"},
        },
    )

    status, error_context = run_test(str(testcase_file), default_cfg)

    assert status is STATUS_FAILED
    assert error_context is not None
    assert error_context["expected"]["response_headers"]["X-Trace-Id"] == "expected-trace"
    assert error_context["actual"]["response_headers"]["x-trace-id"] == "actual-trace"


def test_run_test_write_headers_then_read_headers_roundtrip(httpserver, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    httpserver.expect_request("/api/login").respond_with_json(
        {"ok": True},
        headers={"X-Auth": "Bearer abc123", "X-Ignored": "ignored"},
    )

    seen_request_headers = {}

    def protected_handler(request):
        seen_request_headers["x-auth"] = request.headers.get("X-Auth")
        return Response(
            response=json.dumps({"ok": True}),
            status=200,
            content_type="application/json",
        )

    httpserver.expect_request("/api/protected").respond_with_handler(protected_handler)

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    write_case = write_json_file(
        tests_dir / "01_write_headers.json",
        {
            "url": "/api/login",
            "method": "get",
            "status": 200,
            "response": {"ok": True},
            "write_headers": {"headers.json": ["X-Auth"]},
        },
    )
    read_case = write_json_file(
        tests_dir / "02_read_headers.json",
        {
            "url": "/api/protected",
            "method": "get",
            "status": 200,
            "response": {"ok": True},
            "read_headers": "headers.json",
        },
    )

    try:
        status1, error_context1 = run_test(str(write_case), default_cfg)
        assert status1 is STATUS_OK
        assert error_context1 is None

        saved_headers = json.loads((tmp_path / "headers.json").read_text())
        assert saved_headers == {"X-Auth": "Bearer abc123"}

        status2, error_context2 = run_test(str(read_case), default_cfg)
        assert status2 is STATUS_OK
        assert error_context2 is None
        assert seen_request_headers["x-auth"] == "Bearer abc123"
    finally:
        file_util.cleanup_tmp_files(warn=False, throw=False)


def test_run_fail_fast_stops_before_second_test(httpserver, tmp_path):
    httpserver.expect_request("/api/fail-fast/1").respond_with_json({"ok": False})

    call_counts = {"second": 0}

    def second_handler(_request):
        call_counts["second"] += 1
        return Response(
            response=json.dumps({"ok": True}),
            status=200,
            content_type="application/json",
        )

    httpserver.expect_request("/api/fail-fast/2").respond_with_handler(second_handler)

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    write_json_file(
        tests_dir / "01_fail.json",
        {
            "url": "/api/fail-fast/1",
            "status": 200,
            "response": {"ok": True},
        },
    )
    write_json_file(
        tests_dir / "02_should_not_run.json",
        {
            "url": "/api/fail-fast/2",
            "status": 200,
            "response": {"ok": True},
        },
    )

    cfg_file = write_json_file(
        tmp_path / "cfg.json",
        {
            "tests": str(tests_dir),
            "ext": ".json",
            "base_url": f"http://{FAKE_SERVER}:{FAKE_PORT}",
            "log_level": "ERROR",
            "fail_fast": True,
        },
    )

    result = run_cli_with_args(cfg_file, "-t")

    assert result is False
    assert call_counts["second"] == 0


def test_run_applies_include_then_exclude_filters_in_order(httpserver, tmp_path):
    call_counts = {"target": 0, "drop": 0}

    def target_handler(_request):
        call_counts["target"] += 1
        return Response(
            response=json.dumps({"ok": True}),
            status=200,
            content_type="application/json",
        )

    def drop_handler(_request):
        call_counts["drop"] += 1
        return Response(
            response=json.dumps({"ok": True}),
            status=200,
            content_type="application/json",
        )

    httpserver.expect_request("/api/filter/target").respond_with_handler(target_handler)
    httpserver.expect_request("/api/filter/drop").respond_with_handler(drop_handler)

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    write_json_file(
        tests_dir / "01_target.json",
        {
            "url": "/api/filter/target",
            "status": 200,
            "response": {"ok": True},
        },
    )
    write_json_file(
        tests_dir / "02_drop.json",
        {
            "url": "/api/filter/drop",
            "status": 200,
            "response": {"ok": True},
        },
    )

    cfg_file = write_json_file(
        tmp_path / "cfg.json",
        {
            "tests": str(tests_dir),
            "ext": ".json",
            "base_url": f"http://{FAKE_SERVER}:{FAKE_PORT}",
            "log_level": "ERROR",
        },
    )

    result = run_cli_with_args(cfg_file, "-t", "-i", "target|drop", "-e", "drop")

    assert result is True
    assert call_counts == {"target": 1, "drop": 0}


def test_run_with_t_keeps_temp_files_created_by_write_headers(httpserver, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    clear_tmp_file_registry()

    httpserver.expect_request("/api/temp-headers").respond_with_json(
        {"ok": True},
        headers={"X-Token": "abc123"},
    )

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    write_json_file(
        tests_dir / "01_write_headers.json",
        {
            "url": "/api/temp-headers",
            "status": 200,
            "response": {"ok": True},
            "write_headers": {"headers.json": ["X-Token"]},
        },
    )
    cfg_file = write_json_file(
        tmp_path / "cfg.json",
        {
            "tests": str(tests_dir),
            "ext": ".json",
            "base_url": f"http://{FAKE_SERVER}:{FAKE_PORT}",
            "log_level": "ERROR",
        },
    )

    try:
        result = run_cli_with_args(cfg_file, "-t")
        assert result is True
        assert (tmp_path / "headers.json").is_file()
        assert json.loads((tmp_path / "headers.json").read_text()) == {"X-Token": "abc123"}
    finally:
        file_util.cleanup_tmp_files(warn=False, throw=False)
        clear_tmp_file_registry()


def test_run_without_t_cleans_up_temp_files_created_by_write_headers(httpserver, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    clear_tmp_file_registry()

    httpserver.expect_request("/api/temp-headers-cleanup").respond_with_json(
        {"ok": True},
        headers={"X-Token": "gone-soon"},
    )

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    write_json_file(
        tests_dir / "01_write_headers.json",
        {
            "url": "/api/temp-headers-cleanup",
            "status": 200,
            "response": {"ok": True},
            "write_headers": {"headers.json": ["X-Token"]},
        },
    )
    cfg_file = write_json_file(
        tmp_path / "cfg.json",
        {
            "tests": str(tests_dir),
            "ext": ".json",
            "base_url": f"http://{FAKE_SERVER}:{FAKE_PORT}",
            "log_level": "ERROR",
        },
    )

    try:
        result = run_cli_with_args(cfg_file)
        assert result is True
        assert not (tmp_path / "headers.json").exists()
    finally:
        file_util.cleanup_tmp_files(warn=False, throw=False)
        clear_tmp_file_registry()


def test_run_test_status_only_passes_for_204_without_response_body(httpserver, tmp_path):
    httpserver.expect_request("/api/no-content").respond_with_data("", status=204)
    testcase_file = write_json_file(
        tmp_path / "no_content.json",
        {
            "url": "/api/no-content",
            "method": "get",
            "status": 204,
        },
    )

    status, error_context = run_test(str(testcase_file), default_cfg)

    assert status is STATUS_OK
    assert error_context is None


def test_run_test_sends_query_params_end_to_end(httpserver, tmp_path):
    httpserver.expect_request(
        "/api/search",
        query_string={"q": "skivvy", "page": "2"},
    ).respond_with_json({"ok": True})

    testcase_file = write_json_file(
        tmp_path / "query_params.json",
        {
            "url": "/api/search",
            "method": "get",
            "status": 200,
            "query": {"q": "skivvy", "page": 2},
            "response": {"ok": True},
        },
    )

    status, error_context = run_test(str(testcase_file), default_cfg)

    assert status is STATUS_OK
    assert error_context is None


def test_run_test_inline_headers_override_headers_loaded_from_file(httpserver, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_json_file(tmp_path / "headers.json", {"X-Auth": "from-file", "X-Other": "keep"})

    captured = {}

    def headers_handler(request):
        captured["x-auth"] = request.headers.get("X-Auth")
        captured["x-other"] = request.headers.get("X-Other")
        return Response(
            response=json.dumps({"ok": True}),
            status=200,
            content_type="application/json",
        )

    httpserver.expect_request("/api/with-read-headers").respond_with_handler(headers_handler)

    testcase_file = write_json_file(
        tmp_path / "header_override.json",
        {
            "url": "/api/with-read-headers",
            "method": "get",
            "status": 200,
            "read_headers": "headers.json",
            "headers": {"X-Auth": "inline"},
            "response": {"ok": True},
        },
    )

    status, error_context = run_test(str(testcase_file), default_cfg)

    assert status is STATUS_OK
    assert error_context is None
    assert captured == {"x-auth": "inline", "x-other": "keep"}


def test_run_test_sends_form_payload_end_to_end(httpserver, tmp_path):
    captured = {}

    def form_handler(request):
        captured["username"] = request.form.get("username")
        captured["password"] = request.form.get("password")
        return Response(
            response=json.dumps({"ok": True}),
            status=200,
            content_type="application/json",
        )

    httpserver.expect_request("/api/login-form", method="POST").respond_with_handler(form_handler)

    testcase_file = write_json_file(
        tmp_path / "form_payload.json",
        {
            "url": "/api/login-form",
            "method": "post",
            "status": 200,
            "form": {"username": "alice", "password": "s3cr3t"},
            "headers": {"Content-Type": "application/x-www-form-urlencoded"},
            "response": {"ok": True},
        },
    )

    status, error_context = run_test(str(testcase_file), default_cfg)

    assert status is STATUS_OK
    assert error_context is None
    assert captured == {"username": "alice", "password": "s3cr3t"}

def test_run_test_form_payload_does_not_default_to_json_content_type(httpserver, tmp_path):
    captured = {}

    def form_header_handler(request):
        captured["content_type"] = request.headers.get("Content-Type", "")
        return Response(
            response=json.dumps({"ok": True}),
            status=200,
            content_type="application/json",
        )

    httpserver.expect_request("/api/form-content-type", method="POST").respond_with_handler(
        form_header_handler
    )

    testcase_file = write_json_file(
        tmp_path / "form_content_type.json",
        {
            "url": "/api/form-content-type",
            "method": "post",
            "status": 200,
            "form": {"hello": "world"},
            "response": {"ok": True},
        },
    )

    status, error_context = run_test(str(testcase_file), default_cfg)

    assert status is STATUS_OK
    assert error_context is None
    assert not captured["content_type"].lower().startswith("application/json")

# TODO: Known bug, fix - https://github.com/hyrfilm/skivvy/issues/39
def test_run_test_upload_should_send_file_contents(httpserver, tmp_path):
    upload_file = tmp_path / "payload.txt"
    upload_file.write_text("hello upload")
    captured = {}

    def upload_handler(request):
        file_part = request.files["file"]
        captured["filename"] = file_part.filename
        captured["content"] = file_part.read()
        return Response(
            response=json.dumps({"ok": True}),
            status=200,
            content_type="application/json",
        )

    httpserver.expect_request("/api/upload", method="POST").respond_with_handler(upload_handler)

    testcase_file = write_json_file(
        tmp_path / "upload.json",
        {
            "url": "/api/upload",
            "method": "post",
            "status": 200,
            "upload": {"file": str(upload_file)},
            "response": {"ok": True},
        },
    )

    status, error_context = run_test(str(testcase_file), default_cfg)

    assert status is STATUS_OK
    assert error_context is None
    assert captured["content"] == b"hello upload"

#TODO: This is a known bug: https://github.com/hyrfilm/skivvy/issues/5
@pytest.mark.xfail(
    strict=True,
    reason="$write_file should fail instead of silently overwriting an existing temp file",
)
def test_run_test_duplicate_write_file_filename_should_fail_second_test(httpserver, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    httpserver.expect_request("/api/write-file/1").respond_with_json({"token": "alpha"})
    httpserver.expect_request("/api/write-file/2").respond_with_json({"token": "beta"})

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    first_case = write_json_file(
        tests_dir / "01_write_file.json",
        {
            "url": "/api/write-file/1",
            "status": 200,
            "response": {"token": "$write_file shared-token.txt"},
        },
    )
    second_case = write_json_file(
        tests_dir / "02_write_file_again.json",
        {
            "url": "/api/write-file/2",
            "status": 200,
            "response": {"token": "$write_file shared-token.txt"},
        },
    )

    try:
        status1, error_context1 = run_test(str(first_case), default_cfg)
        status2, error_context2 = run_test(str(second_case), default_cfg)

        assert status1 is STATUS_OK
        assert error_context1 is None
        assert status2 is STATUS_FAILED
        assert error_context2 is not None
    finally:
        file_util.cleanup_tmp_files(warn=False, throw=False)


# ── Event tests ──────────────────────────────────────────────────────────
#
# Unit tests for the events module and integration tests verifying that
# events are emitted correctly during run_test() execution.
# ─────────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=False)
def clean_event_context():
    """Reset event context between tests to prevent leakage."""
    token = events._event_context.set({})
    yield
    events._event_context.reset(token)


def _connect(signal_name, receiver):
    """Connect a receiver and return a disconnect callable."""
    sig = events.signal(signal_name)
    sig.connect(receiver)
    return lambda: sig.disconnect(receiver)


# ── events module: unit tests ────────────────────────────────────────────


def test_emit_delivers_payload(clean_event_context):
    captured = []
    disconnect = _connect("test.custom", lambda _s, **kw: captured.append(kw))
    try:
        events.emit("test.custom", foo="bar")
    finally:
        disconnect()

    assert len(captured) == 1
    assert captured[0]["event"] == "test.custom"
    assert captured[0]["foo"] == "bar"


def test_emit_includes_timestamp(clean_event_context):
    import time as _time

    captured = []
    disconnect = _connect("test.ts", lambda _s, **kw: captured.append(kw))
    before = int(_time.time() * 1000)
    try:
        events.emit("test.ts")
    finally:
        disconnect()
    after = int(_time.time() * 1000)

    ts = captured[0]["ts"]
    assert before <= ts <= after


def test_emit_merges_context(clean_event_context):
    captured = []
    disconnect = _connect("test.ctx", lambda _s, **kw: captured.append(kw))
    try:
        with events.with_context(run_id="abc"):
            events.emit("test.ctx", extra="val")
    finally:
        disconnect()

    assert captured[0]["run_id"] == "abc"
    assert captured[0]["extra"] == "val"


def test_with_context_nesting_and_restore(clean_event_context):
    captured = []
    disconnect = _connect("test.nest", lambda _s, **kw: captured.append(kw))
    try:
        with events.with_context(a="1"):
            with events.with_context(b="2"):
                events.emit("test.nest")
            events.emit("test.nest")
    finally:
        disconnect()

    # Inner: both a and b
    assert captured[0]["a"] == "1"
    assert captured[0]["b"] == "2"
    # Outer: only a (b restored away)
    assert captured[1]["a"] == "1"
    assert "b" not in captured[1]


def test_with_context_skips_none_values(clean_event_context):
    with events.with_context(a="1", b=None):
        ctx = events.current_context()
    assert ctx["a"] == "1"
    assert "b" not in ctx


def test_emit_catches_subscriber_exception(clean_event_context):
    def bad_receiver(_sender, **kw):
        raise RuntimeError("boom")

    disconnect = _connect("test.boom", bad_receiver)
    try:
        result = events.emit("test.boom")
    finally:
        disconnect()

    # Should not raise, returns empty list on error
    assert result == []


def test_phase_span_emits_started_and_finished(clean_event_context):
    captured = []
    disc1 = _connect(events.TEST_PHASE_STARTED, lambda _s, **kw: captured.append(("started", kw)))
    disc2 = _connect(events.TEST_PHASE_FINISHED, lambda _s, **kw: captured.append(("finished", kw)))
    try:
        with events.phase_span("my_phase", testfile="f.json"):
            pass
    finally:
        disc1()
        disc2()

    assert len(captured) == 2
    assert captured[0][0] == "started"
    assert captured[0][1]["phase"] == "my_phase"
    assert captured[0][1]["testfile"] == "f.json"
    assert captured[1][0] == "finished"
    assert captured[1][1]["phase"] == "my_phase"
    assert captured[1][1]["elapsed_ms"] >= 0


def test_phase_span_emits_failed_on_exception(clean_event_context):
    captured = []
    disc1 = _connect(events.TEST_PHASE_FAILED, lambda _s, **kw: captured.append(kw))
    try:
        with pytest.raises(ValueError, match="boom"):
            with events.phase_span("bad_phase"):
                raise ValueError("boom")
    finally:
        disc1()

    assert len(captured) == 1
    assert captured[0]["phase"] == "bad_phase"
    assert captured[0]["error"] == "boom"
    assert captured[0]["error_type"] == "ValueError"
    assert captured[0]["elapsed_ms"] >= 0


def test_phase_span_does_not_emit_finished_on_exception(clean_event_context):
    finished = []
    disc1 = _connect(events.TEST_PHASE_FINISHED, lambda _s, **kw: finished.append(kw))
    try:
        with pytest.raises(ValueError):
            with events.phase_span("bad_phase"):
                raise ValueError("boom")
    finally:
        disc1()

    assert finished == []


def test_signal_returns_same_instance():
    assert events.signal("same_name") is events.signal("same_name")


# ── events: integration tests with run_test() ───────────────────────────


def test_run_test_emits_phase_events_on_success(httpserver):
    httpserver.expect_request("/api/fortune/1").respond_with_json(
        {"wisdom": "If it seems that fates are aginst you today, they probably are."}
    )

    captured = []
    disc1 = _connect(events.TEST_PHASE_STARTED, lambda _s, **kw: captured.append(("started", kw["phase"])))
    disc2 = _connect(events.TEST_PHASE_FINISHED, lambda _s, **kw: captured.append(("finished", kw["phase"])))
    try:
        status, _ = run_test(
            "./tests/fixtures/testcases/check_status.json", default_cfg
        )
    finally:
        disc1()
        disc2()

    assert status is STATUS_OK
    phases = [name for _, name in captured]
    # Core phases in order
    assert "create_testcase" in phases
    assert "create_request" in phases
    assert "http_execute" in phases
    assert "http_transport" in phases
    assert "verify_status" in phases
    # Each started has a matching finished
    started_phases = [name for kind, name in captured if kind == "started"]
    finished_phases = [name for kind, name in captured if kind == "finished"]
    for phase in started_phases:
        assert phase in finished_phases


def test_run_test_emits_phase_failed_on_verify_mismatch(httpserver):
    httpserver.expect_request("/api/fortune/1").respond_with_json(
        {"wisdom": "If it seems that fates are aginst you today, they probably are."}
    )

    failed_phases = []
    disc = _connect(events.TEST_PHASE_FAILED, lambda _s, **kw: failed_phases.append(kw))
    try:
        status, err_context = run_test(
            "./tests/fixtures/testcases/check_exact_match.json", default_cfg
        )
    finally:
        disc()

    assert status is STATUS_FAILED
    assert len(failed_phases) == 1
    assert failed_phases[0]["phase"] == "verify_response"
    assert "error" in failed_phases[0]
    assert "error_type" in failed_phases[0]
    assert failed_phases[0]["elapsed_ms"] >= 0


def test_run_test_successful_phases_still_finish_before_failure(httpserver):
    httpserver.expect_request("/api/fortune/1").respond_with_json(
        {"wisdom": "If it seems that fates are aginst you today, they probably are."}
    )

    finished = []
    failed = []
    disc1 = _connect(events.TEST_PHASE_FINISHED, lambda _s, **kw: finished.append(kw["phase"]))
    disc2 = _connect(events.TEST_PHASE_FAILED, lambda _s, **kw: failed.append(kw["phase"]))
    try:
        status, _ = run_test(
            "./tests/fixtures/testcases/check_exact_match.json", default_cfg
        )
    finally:
        disc1()
        disc2()

    assert status is STATUS_FAILED
    # Earlier phases completed successfully
    assert "create_testcase" in finished
    assert "create_request" in finished
    assert "http_execute" in finished
    assert "http_transport" in finished
    assert "verify_status" in finished
    # The failing phase did not finish — it failed
    assert "verify_response" not in finished
    assert "verify_response" in failed


def test_run_test_phase_events_carry_testfile(httpserver):
    httpserver.expect_request("/api/fortune/1").respond_with_json(
        {"wisdom": "If it seems that fates are aginst you today, they probably are."}
    )

    captured = []
    disc = _connect(events.TEST_PHASE_STARTED, lambda _s, **kw: captured.append(kw))
    try:
        run_test("./tests/fixtures/testcases/check_status.json", default_cfg)
    finally:
        disc()

    assert len(captured) > 0
    # Phases instrumented in run_test() carry testfile explicitly
    phases_with_testfile = [e for e in captured if "testfile" in e]
    assert len(phases_with_testfile) >= 3  # at least create_testcase, create_request, http_execute
    assert all(
        e["testfile"] == "./tests/fixtures/testcases/check_status.json"
        for e in phases_with_testfile
    )
    # http_transport (in http_util.py) carries http_method/url instead
    transport_phases = [e for e in captured if e["phase"] == "http_transport"]
    assert len(transport_phases) == 1
    assert "http_method" in transport_phases[0]
