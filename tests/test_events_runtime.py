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
    previous = dict(events._context)
    events._context.clear()
    yield
    events._context.clear()
    events._context.update(previous)


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


def test_run_test_emits_phase_events_on_success(httpserver, tmp_path, clean_event_context):
    httpserver.expect_request("/api/ok").respond_with_json({"ok": True})
    testcase_file = write_json_file(
        tmp_path / "ok.json",
        {"url": "/api/ok", "method": "get", "status": 200, "response": {"ok": True}},
    )

    captured = []
    disc1 = _connect(events.TEST_PHASE_STARTED, lambda _s, **kw: captured.append(("started", kw)))
    disc2 = _connect(events.TEST_PHASE_FINISHED, lambda _s, **kw: captured.append(("finished", kw)))
    try:
        status, err = run_test(
            str(testcase_file),
            {"base_url": _base_url(httpserver), "log_level": "ERROR"},
        )
    finally:
        disc1()
        disc2()

    assert status is STATUS_OK
    assert err is None
    phases = [entry[1]["phase"] for entry in captured]
    assert "create_testcase" in phases
    assert "create_request" in phases
    assert "http_execute" in phases
    assert "http_transport" in phases
    assert "verify_status" in phases
    assert "verify_response" in phases


def test_subscriber_failure_during_testcase_event_fails_run_test(tmp_path, clean_event_context):
    testcase_file = write_json_file(
        tmp_path / "boom.json",
        {"url": "/api/will-not-run", "method": "get", "status": 200},
    )

    def bad_receiver(_sender, **kw):
        raise RuntimeError("sink boom")

    disc = _connect(events.TEST_PHASE_STARTED, bad_receiver)
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


def test_install_runtime_sinks_temporary_flags_toggle_paths(clean_event_context):
    install = sinks.install_runtime_sinks({"_rich": True, "_timing": True, "_http_timing": True})
    try:
        assert install.terminal_sink is not None
        assert install.error_sink is not None
        assert install.timing_sink is not None
        assert install.terminal_sink.renderer == "rich"
        assert install.timing_sink.http_timing is True
    finally:
        install.close()

    install = sinks.install_runtime_sinks({"_rich": False})
    try:
        assert install.terminal_sink is not None
        assert install.error_sink is not None
        assert install.terminal_sink.renderer == "plain"
        assert install.timing_sink is None
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
        with events.with_context(test_id="case-1", testfile="case-1"):
            events.emit(events.TEST_STARTED, ts=1000)
            events.emit(events.TEST_PHASE_STARTED, phase="http_transport", ts=1010)
            events.emit(
                events.TEST_PHASE_FINISHED,
                phase="http_transport",
                ts=1045,
                elapsed_ms=999999,
            )
            events.emit(events.TEST_FINISHED, ts=1125, elapsed_ms=1, success=True)
    finally:
        timing_sink.close()

    assert timing_sink.test_totals_ms["case-1"] == 125
    assert timing_sink.phase_durations_ms["case-1"]["http_transport"] == 35
    assert timing_sink.http_phase_durations_ms["case-1"] == [35]


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
    assert seen[-1][1]["elapsed_ms"] >= 0


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
