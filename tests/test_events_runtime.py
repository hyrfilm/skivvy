import json
import sys

import pytest

from skivvy import events, sinks
from skivvy.skivvy import run, run_test, STATUS_FAILED, STATUS_OK

FAKE_SERVER = "localhost"
FAKE_PORT = 8888


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


def _base_url(httpserver):
    return httpserver.url_for("/").rstrip("/")


def _connect(signal_name, receiver):
    sig = events.signal(signal_name)
    sig.connect(receiver)
    return lambda: sig.disconnect(receiver)


@pytest.fixture
def clean_event_context():
    events.reset_runtime_listener()
    yield
    events.reset_runtime_listener()


@pytest.fixture(scope="session")
def httpserver_listen_address():
    return (FAKE_SERVER, FAKE_PORT)


def test_emit_delivers_payload_and_timestamp(clean_event_context):
    captured = []
    disconnect = _connect("test.custom", lambda _s, **kw: captured.append(kw))
    try:
        events.emit("test.custom", foo="bar")
    finally:
        disconnect()

    assert len(captured) == 1
    assert captured[0]["event"] == "test.custom"
    assert captured[0]["foo"] == "bar"
    assert isinstance(captured[0]["ts"], int)


def test_emit_propagates_subscriber_exception(clean_event_context):
    def bad_receiver(_sender, **kw):
        raise RuntimeError("boom")

    disconnect = _connect("test.boom", bad_receiver)
    try:
        with pytest.raises(RuntimeError, match="boom"):
            events.emit("test.boom")
    finally:
        disconnect()


def test_run_test_emits_step_events_on_success(httpserver, tmp_path, clean_event_context):
    httpserver.expect_request("/api/ok").respond_with_json({"ok": True})
    testcase_file = write_json_file(
        tmp_path / "ok.json",
        {"url": "/api/ok", "method": "get", "status": 200, "response": {"ok": True}},
    )

    captured = []
    step_events = [
        events.CREATE_TESTCASE,
        events.CREATE_REQUEST,
        events.EXECUTE_REQUEST,
        events.HTTP_TRANSPORT,
        events.VERIFY_STATUS,
        events.VERIFY_RESPONSE,
    ]
    disconnects = [
        _connect(signal_name, lambda _s, signal_name=signal_name, **kw: captured.append((signal_name, kw)))
        for signal_name in step_events
    ]
    try:
        status, err = run_test(
            str(testcase_file),
            {"base_url": _base_url(httpserver), "log_level": "ERROR"},
        )
    finally:
        for disconnect in reversed(disconnects):
            disconnect()

    assert status is STATUS_OK
    assert err is None
    seen_steps = [event_name for event_name, _ in captured]
    assert seen_steps == step_events


def test_subscriber_failure_during_testcase_event_fails_run_test(tmp_path, clean_event_context):
    testcase_file = write_json_file(
        tmp_path / "boom.json",
        {"url": "/api/will-not-run", "method": "get", "status": 200},
    )

    def bad_receiver(_sender, **kw):
        raise RuntimeError("sink boom")

    disc = _connect(events.CREATE_TESTCASE, bad_receiver)
    try:
        status, err = run_test(
            str(testcase_file),
            {"base_url": "http://127.0.0.1:1", "log_level": "ERROR"},
        )
    finally:
        disc()

    assert status is STATUS_FAILED
    assert err is not None
    assert "sink boom" in err["exception"]
    assert "traceback" in err
    assert "Traceback" in err["traceback"]
    assert err["failed_step"] == events.CREATE_TESTCASE


def test_install_runtime_sinks_installs_console_and_optional_timing(clean_event_context):
    install = sinks.install_runtime_sinks({"_timing": True, "_http_timing": True})
    try:
        assert install.console_sink is not None
        assert install.timing_sink is not None
        assert isinstance(install.console_sink, sinks.ConsoleOutputSink)
        assert install.timing_sink.http_timing is True
    finally:
        install.close()

    install = sinks.install_runtime_sinks({})
    try:
        assert install.console_sink is not None
        assert isinstance(install.console_sink, sinks.ConsoleOutputSink)
        assert install.timing_sink is None
    finally:
        install.close()

    install = sinks.install_runtime_sinks(
        {
            "diff_enabled": True,
            "diff_ndiff": False,
            "diff_unified": True,
            "diff_table": True,
            "diff_full": True,
            "diff_compact_lists": False,
            "http_request_level": "INFO",
            "http_response_level": "WARNING",
            "http_headers_level": None,
        }
    )
    try:
        assert install.console_sink.diff_enabled is True
        assert install.console_sink.diff_ndiff is False
        assert install.console_sink.diff_unified is True
        assert install.console_sink.diff_table is True
        assert install.console_sink.diff_full is True
        assert install.console_sink.diff_compact_lists is False
        assert install.console_sink.http_request_level == "INFO"
        assert install.console_sink.http_response_level == "WARNING"
        assert install.console_sink.http_headers_level is None
    finally:
        install.close()

    install = sinks.install_runtime_sinks({"_http_timing": True})
    try:
        assert install.timing_sink is None
    finally:
        install.close()


def test_timing_sink_computes_from_ts_not_elapsed_ms(clean_event_context):
    timing_sink = sinks.TimingSink(http_timing=True).install()
    try:
        events.emit(events.TEST_STARTED, test_id="case-1", testfile="case-1", ts=1000)
        events.emit(events.HTTP_TRANSPORT, ts=1010)
        events.emit(events.VERIFY_STATUS, ts=1045)
        events.emit(events.TEST_FINISHED, ts=1125, success=True)
    finally:
        timing_sink.close()

    assert timing_sink.test_totals_ms["case-1"] == 125
    assert timing_sink.phase_durations_ms["case-1"][events.HTTP_TRANSPORT] == 35
    assert timing_sink.http_phase_durations_ms["case-1"] == [35]


def test_project_failure_payload_status_focuses_only_status():
    expected, actual = sinks._project_failure_payload(
        {
            "failed_step": events.VERIFY_STATUS,
            "expected": {
                "status": 200,
                "response": {"ok": True},
                "response_headers": {"x": "1"},
            },
            "actual": {
                "status": 500,
                "response": {"ok": False},
                "response_headers": {"x": "2"},
            },
        }
    )

    assert expected == {"status": 200}
    assert actual == {"status": 500}


def test_project_failure_payload_response_prunes_equal_fields():
    expected, actual = sinks._project_failure_payload(
        {
            "failed_step": events.VERIFY_RESPONSE,
            "expected": {
                "response": {
                    "a": 1,
                    "b": 2,
                    "nested": {"x": 1, "y": 2},
                }
            },
            "actual": {
                "response": {
                    "a": 1,
                    "b": 3,
                    "nested": {"x": 1, "y": 9},
                    "ignored": True,
                }
            },
        }
    )

    assert expected == {"response": {"b": 2, "nested": {"y": 2}}}
    assert actual == {"response": {"b": 3, "nested": {"y": 9}}}


def test_project_failure_payload_headers_focuses_only_headers():
    expected, actual = sinks._project_failure_payload(
        {
            "failed_step": events.VERIFY_RESPONSE_HEADERS,
            "expected": {
                "status": 200,
                "response_headers": {"x": "1"},
            },
            "actual": {
                "status": 200,
                "response_headers": {"x": "2"},
            },
        }
    )

    assert expected == {"response_headers": {"x": "1"}}
    assert actual == {"response_headers": {"x": "2"}}


def test_project_failure_payload_response_compacts_large_actual_lists():
    expected, actual = sinks._project_failure_payload(
        {
            "failed_step": events.VERIFY_RESPONSE,
            "expected": {
                "response": [
                    {
                        "id": 1,
                        "name": "alpha",
                    }
                ]
            },
            "actual": {
                "response": [
                    {
                        "id": index,
                        "name": "name-value-that-is-quite-long-to-trigger-compaction",
                        "ignored": "x" * 20,
                    }
                    for index in range(500)
                ]
            },
        }
    )

    assert expected == {"response": [{"id": 1, "name": "alpha"}]}
    compacted_list = actual["response"]
    assert len(compacted_list) == 5
    assert compacted_list[-1]["__omitted_items__"] == 496
    assert compacted_list[-1]["total_items"] == 500
    omitted_markers = sinks._collect_omitted_markers(actual)
    assert len(omitted_markers) == 1


def test_project_failure_payload_response_keeps_small_lists_uncompacted():
    expected, actual = sinks._project_failure_payload(
        {
            "failed_step": events.VERIFY_RESPONSE,
            "expected": {
                "response": [
                    {"id": 1},
                    {"id": 2},
                ]
            },
            "actual": {
                "response": [
                    {"id": 1},
                    {"id": 3},
                ]
            },
        }
    )

    assert expected == {"response": [{"id": 1}, {"id": 2}]}
    assert actual == {"response": [{"id": 1}, {"id": 3}]}
    assert sinks._collect_omitted_markers(actual) == []


def test_project_failure_payload_can_disable_list_compaction():
    expected, actual = sinks._project_failure_payload(
        {
            "failed_step": events.VERIFY_RESPONSE,
            "expected": {"response": [{"id": 1}]},
            "actual": {
                "response": [{"id": idx, "ignored": "x" * 100} for idx in range(100)]
            },
        },
        compact_lists=False,
    )

    assert expected == {"response": [{"id": 1}]}
    assert len(actual["response"]) == 100
    assert sinks._collect_omitted_markers(actual) == []


def test_console_sink_uses_table_renderer_when_enabled(monkeypatch):
    rendered = []

    def capture_render(renderable):
        rendered.append(renderable)

    monkeypatch.setattr(sinks.log, "render", capture_render)
    monkeypatch.setattr(sinks.log, "info", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(sinks.log, "error", lambda *_args, **_kwargs: None)

    sink = sinks.ConsoleOutputSink(
        {
            "diff_ndiff": False,
            "diff_unified": False,
            "diff_table": True,
            "diff_full": False,
        }
    )
    sink._log_failure_context(
        {
            "failed_step": events.VERIFY_RESPONSE,
            "exception": "boom",
            "expected": {"response": {"a": 1}},
            "actual": {"response": {"a": 2}},
        }
    )

    assert len(rendered) == 1


def test_console_sink_diff_full_bypasses_projection(monkeypatch):
    monkeypatch.setattr(
        sinks,
        "_project_failure_payload",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("unexpected")),
    )
    monkeypatch.setattr(sinks.log, "info", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(sinks.log, "error", lambda *_args, **_kwargs: None)

    sink = sinks.ConsoleOutputSink(
        {
            "diff_ndiff": False,
            "diff_unified": False,
            "diff_table": False,
            "diff_full": True,
        }
    )
    sink._log_failure_context(
        {
            "failed_step": events.VERIFY_RESPONSE,
            "exception": "boom",
            "expected": {"response": {"a": 1, "same": 10}},
            "actual": {"response": {"a": 2, "same": 10}},
        }
    )


def test_console_sink_http_logging_uses_individual_levels(monkeypatch):
    emitted = []

    def capture(level, msg, new_line=True):
        if level is None:
            return
        emitted.append((level, msg, new_line))

    monkeypatch.setattr(sinks.log, "log_at", capture)

    sink = sinks.ConsoleOutputSink(
        {
            "http_request_level": "INFO",
            "http_response_level": None,
            "http_headers_level": "WARNING",
        }
    )
    sink._on_http_transport(
        None,
        http_method="get",
        url="http://example.test/api",
        request_query={"a": 1},
        request_headers={"x-request": "123"},
    )
    sink._on_http_response(
        None,
        http_status=200,
        url="http://example.test/api",
        response_body='{"ok": true}',
        response_headers={"x-response": "456"},
    )

    assert any(level == "INFO" and "http request" in msg for level, msg, _ in emitted)
    assert any(
        level == "WARNING" and "request headers" in msg for level, msg, _ in emitted
    )
    assert any(
        level == "WARNING" and "response headers" in msg for level, msg, _ in emitted
    )
    assert not any("http response" in msg for _level, msg, _ in emitted)


def test_run_emits_run_passed_then_finished_with_timestamps(httpserver, tmp_path, clean_event_context):
    httpserver.expect_request("/api/pass").respond_with_json({"ok": True})

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    write_json_file(
        tests_dir / "01.json",
        {"url": "/api/pass", "status": 200, "response": {"ok": True}},
    )
    cfg_file = write_json_file(
        tmp_path / "cfg.json",
        {
            "tests": str(tests_dir),
            "ext": ".json",
            "base_url": _base_url(httpserver),
            "log_level": "ERROR",
            "file_order": "lexical",
        },
    )

    seen = []
    discs = [
        _connect(events.RUN_STARTED, lambda _s, **kw: seen.append(("run.started", kw))),
        _connect(events.RUN_PASSED, lambda _s, **kw: seen.append(("run.passed", kw))),
        _connect(events.RUN_FINISHED, lambda _s, **kw: seen.append(("run.finished", kw))),
    ]
    try:
        assert run_cli_with_args(cfg_file, "-t") is True
    finally:
        for disc in reversed(discs):
            disc()

    assert [name for name, _ in seen] == ["run.started", "run.passed", "run.finished"]
    assert all(isinstance(payload["ts"], int) for _, payload in seen)
    assert seen[-1][1]["success"] is True
    assert seen[-1][1]["num_tests"] == 1
    assert seen[-1][1]["failures"] == 0
    assert "elapsed_ms" not in seen[-1][1]


def test_run_emits_run_failed_then_finished(httpserver, tmp_path, clean_event_context):
    httpserver.expect_request("/api/fail").respond_with_json({"ok": True})

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    write_json_file(
        tests_dir / "01.json",
        {"url": "/api/fail", "status": 201, "response": {"ok": True}},
    )
    cfg_file = write_json_file(
        tmp_path / "cfg.json",
        {
            "tests": str(tests_dir),
            "ext": ".json",
            "base_url": _base_url(httpserver),
            "log_level": "ERROR",
            "file_order": "lexical",
        },
    )

    seen = []
    discs = [
        _connect(events.RUN_STARTED, lambda _s, **kw: seen.append(("run.started", kw))),
        _connect(events.RUN_FAILED, lambda _s, **kw: seen.append(("run.failed", kw))),
        _connect(events.RUN_FINISHED, lambda _s, **kw: seen.append(("run.finished", kw))),
    ]
    try:
        assert run_cli_with_args(cfg_file, "-t") is False
    finally:
        for disc in reversed(discs):
            disc()

    assert [name for name, _ in seen] == ["run.started", "run.failed", "run.finished"]
    assert seen[1][1]["success"] is False
    assert seen[2][1]["success"] is False
    assert seen[2][1]["failures"] == 1


def test_run_emits_run_finished_even_when_test_started_subscriber_raises(
    httpserver, tmp_path, clean_event_context
):
    httpserver.expect_request("/api/pass").respond_with_json({"ok": True})

    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    write_json_file(tests_dir / "01.json", {"url": "/api/pass", "status": 200})
    cfg_file = write_json_file(
        tmp_path / "cfg.json",
        {
            "tests": str(tests_dir),
            "ext": ".json",
            "base_url": _base_url(httpserver),
            "log_level": "ERROR",
            "file_order": "lexical",
        },
    )

    finished = []

    def bad_receiver(_sender, **kw):
        raise RuntimeError("sink boom")

    disc_bad = _connect(events.TEST_STARTED, bad_receiver)
    disc_finished = _connect(events.RUN_FINISHED, lambda _s, **kw: finished.append(kw))
    try:
        with pytest.raises(RuntimeError, match="sink boom"):
            run_cli_with_args(cfg_file, "-t")
    finally:
        disc_finished()
        disc_bad()

    assert len(finished) == 1
    assert finished[0]["event"] == events.RUN_FINISHED
    assert "ts" in finished[0]
