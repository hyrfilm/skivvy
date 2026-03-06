from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
import json
from typing import Callable

from . import events
from .config import Settings, conf_get
from .util import log
from .util import str_util
from .util.icdiff2 import RichConsoleDiff
from .util.str_util import tojsonstr


Disconnect = Callable[[], None]
_MISSING = "<missing>"
_OMIT = object()
_OMITTED_MARKER_KEY = "__omitted_items__"
_LIST_COMPACT_MIN_ACTUAL_ITEMS = 25
_LIST_COMPACT_MIN_EXTRA_ITEMS = 8
_LIST_COMPACT_RATIO_THRESHOLD = 3
_LIST_SAMPLE_LIMIT = 4


def _should_compact_list(expected: list, actual: list) -> bool:
    actual_len = len(actual)
    expected_len = max(len(expected), 1)
    if actual_len < _LIST_COMPACT_MIN_ACTUAL_ITEMS:
        return False
    if actual_len < len(expected) + _LIST_COMPACT_MIN_EXTRA_ITEMS:
        return False
    return actual_len >= expected_len * _LIST_COMPACT_RATIO_THRESHOLD


def _project_item_to_expected_surface(template: object, item: object) -> object:
    if isinstance(template, dict) and isinstance(item, dict):
        projected = {}
        for key, expected_value in template.items():
            projected[key] = item.get(key, _MISSING)
            if key in item and isinstance(expected_value, dict) and isinstance(item[key], dict):
                projected[key] = _project_item_to_expected_surface(expected_value, item[key])
        return projected
    return item


def _compact_actual_list_against_expected(expected: list, actual: list) -> list:
    if not actual:
        return actual

    if len(expected) == 1:
        template = expected[0]
        sample = [
            _project_item_to_expected_surface(template, item)
            for item in actual[:_LIST_SAMPLE_LIMIT]
        ]
    else:
        sample = []
        for index, item in enumerate(actual[:_LIST_SAMPLE_LIMIT]):
            template = expected[min(index, len(expected) - 1)]
            sample.append(_project_item_to_expected_surface(template, item))

    omitted = len(actual) - len(sample)
    if omitted > 0:
        sample.append({_OMITTED_MARKER_KEY: omitted, "total_items": len(actual)})
    return sample


def _collect_omitted_markers(value: object) -> list[dict]:
    found: list[dict] = []
    if isinstance(value, dict):
        if _OMITTED_MARKER_KEY in value:
            found.append(value)
        for nested in value.values():
            found.extend(_collect_omitted_markers(nested))
    elif isinstance(value, list):
        for item in value:
            found.extend(_collect_omitted_markers(item))
    return found


def _prune_equal_within_expected_surface(
    expected: object,
    actual: object,
    compact_lists: bool = True,
):
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return expected, actual

        expected_out = {}
        actual_out = {}
        for key, expected_value in expected.items():
            if key not in actual:
                expected_out[key] = expected_value
                actual_out[key] = _MISSING
                continue

            pruned_expected, pruned_actual = _prune_equal_within_expected_surface(
                expected_value, actual[key]
            )
            if pruned_expected is _OMIT:
                continue
            expected_out[key] = pruned_expected
            actual_out[key] = pruned_actual

        if not expected_out:
            return _OMIT, _OMIT
        return expected_out, actual_out

    if isinstance(expected, list):
        if not isinstance(actual, list):
            return expected, actual
        if expected == actual:
            return _OMIT, _OMIT
        if compact_lists and _should_compact_list(expected, actual):
            return expected, _compact_actual_list_against_expected(expected, actual)
        return expected, actual

    if expected == actual:
        return _OMIT, _OMIT
    return expected, actual


def _project_failure_payload(
    err_context: dict,
    compact_lists: bool = True,
) -> tuple[object, object]:
    expected = err_context.get("expected")
    actual = err_context.get("actual")
    failed_step = err_context.get("failed_step")

    if not isinstance(expected, dict) or not isinstance(actual, dict):
        return expected, actual

    if failed_step == events.VERIFY_STATUS:
        return {"status": expected.get("status")}, {"status": actual.get("status")}

    if failed_step == events.VERIFY_RESPONSE:
        expected_response = expected.get("response")
        actual_response = actual.get("response")
        pruned_expected, pruned_actual = _prune_equal_within_expected_surface(
            expected_response,
            actual_response,
            compact_lists=compact_lists,
        )
        if pruned_expected is _OMIT:
            return {"response": expected_response}, {"response": actual_response}
        return {"response": pruned_expected}, {"response": pruned_actual}

    if failed_step == events.VERIFY_RESPONSE_HEADERS:
        return {"response_headers": expected.get("response_headers")}, {
            "response_headers": actual.get("response_headers")
        }

    return expected, actual


class BaseSink:
    def __init__(self):
        self._disconnects: list[Disconnect] = []

    def _connect(self, signal_name: str, receiver):
        sig = events.signal(signal_name)
        sig.connect(receiver)
        self._disconnects.append(lambda: sig.disconnect(receiver))

    def close(self):
        for disconnect in reversed(self._disconnects):
            disconnect()
        self._disconnects.clear()


class ConsoleOutputSink(BaseSink):
    def __init__(self, conf: dict | None = None):
        super().__init__()
        conf = conf or {}
        self.diff_enabled = bool(conf.get("diff_enabled", True))
        self.diff_ndiff = bool(conf.get("diff_ndiff", True))
        self.diff_unified = bool(conf.get("diff_unified", False))
        self.diff_table = bool(conf.get("diff_table", False))
        self.diff_full = bool(conf.get("diff_full", False))
        self.diff_compact_lists = bool(conf.get("diff_compact_lists", True))
        self.http_request_level = conf.get("http_request_level", "DEBUG")
        self.http_response_level = conf.get("http_response_level", "DEBUG")
        self.http_headers_level = conf.get("http_headers_level", "DEBUG")

    def install(self):
        self._connect(events.RUN_STARTED, self._on_run_started)
        self._connect(events.TEST_PASSED, self._on_test_passed)
        self._connect(events.TEST_FAILED, self._on_test_failed)
        self._connect(events.RUN_FINISHED, self._on_run_finished)
        self._connect(events.HTTP_TRANSPORT, self._on_http_transport)
        self._connect(events.HTTP_RESPONSE, self._on_http_response)
        return self

    def _on_run_started(self, _sender, **kw):
        log.info(f"[b]skivvy[/b] [u]{kw.get('version')}[/u] | config={kw.get('config_file')}")
        log.info(f"{kw.get('test_count')} tests found.")

    def _on_test_passed(self, _sender, **kw):
        log.info(f"{kw.get('testfile')}\t[green]OK[/green]")

    def _on_test_failed(self, _sender, **kw):
        log.error(f"\n\n[red]{kw.get('testfile')}\tFAILED[/red]\n")
        self._log_failure_context(kw.get("error_context") or {})
        log.error("\n")

    def _on_run_finished(self, _sender, **kw):
        failures = kw.get("failures") or 0
        num_tests = kw.get("num_tests") or 0
        if failures > 0:
            log.info(f"{failures} testcases of {num_tests} failed. :(")
        elif num_tests == 0:
            log.info("No tests found!")
        else:
            log.info(f"All {num_tests} tests passed.")
            log.info("Lookin' good!")

    def _log_failure_context(self, err_context: dict):
        failed_step = err_context.get("failed_step")
        if failed_step:
            log.info(f"[dim]failed_step={failed_step}[/dim]")

        e = err_context.get("exception")
        tb = err_context.get("traceback")
        expected = err_context.get("expected")
        actual = err_context.get("actual")
        if e:
            log.error(str(e))
        if tb:
            log.error(tb)
        if expected is not None and self.diff_enabled:
            if self.diff_full:
                projected_expected, projected_actual = expected, actual
            else:
                projected_expected, projected_actual = _project_failure_payload(
                    err_context,
                    compact_lists=self.diff_compact_lists,
                )
                omitted_markers = _collect_omitted_markers(projected_actual)
                if omitted_markers:
                    summaries = []
                    for marker in omitted_markers:
                        summaries.append(
                            f"omitted {marker.get('__omitted_items__')} of {marker.get('total_items')} actual list items"
                        )
                    log.info(
                        f"[dim]heuristic compaction applied: {'; '.join(summaries)}[/dim]"
                    )
            expected_json = tojsonstr(projected_expected)
            actual_json = tojsonstr(projected_actual)

            if self.diff_ndiff:
                self._log_text_diff("ndiff", expected_json, actual_json)
            if self.diff_unified:
                self._log_text_diff("unified", expected_json, actual_json)
            if self.diff_table:
                self._log_table_diff(expected_json, actual_json)

    def _on_http_transport(self, _sender, **kw):
        method = (kw.get("http_method") or "").upper()
        url = kw.get("url")
        log.log_at(self.http_request_level, f"[dim]http request[/dim] {method} {url}")

        payload = {}
        if kw.get("request_query") is not None:
            payload["query"] = kw.get("request_query")
        if kw.get("request_json") is not None:
            payload["json"] = kw.get("request_json")
        if kw.get("request_data") is not None:
            payload["data"] = kw.get("request_data")
        if kw.get("request_upload_fields"):
            payload["upload_fields"] = kw.get("request_upload_fields")
        if payload:
            log.log_at(self.http_request_level, tojsonstr(payload))

        request_headers = kw.get("request_headers")
        if request_headers:
            log.log_at(
                self.http_headers_level,
                f"[dim]request headers[/dim]\n{tojsonstr(request_headers)}",
            )

    def _on_http_response(self, _sender, **kw):
        status = kw.get("http_status")
        url = kw.get("url")
        log.log_at(
            self.http_response_level,
            f"[dim]http response[/dim] status={status} url={url}",
        )

        response_body = kw.get("response_body")
        if response_body:
            log.log_at(self.http_response_level, self._format_http_body(response_body))

        response_headers = kw.get("response_headers")
        if response_headers:
            log.log_at(
                self.http_headers_level,
                f"[dim]response headers[/dim]\n{tojsonstr(response_headers)}",
            )

    def _format_http_body(self, response_body: object) -> str:
        if isinstance(response_body, bytes):
            return response_body.decode("utf-8", errors="replace")
        if not isinstance(response_body, str):
            return str(response_body)

        try:
            return tojsonstr(json.loads(response_body))
        except Exception:
            return response_body

    def _log_text_diff(self, diff_type: str, expected_json: str, actual_json: str):
        log.info(f"--------------- DIFF ({diff_type}) BEGIN ---------------")
        diff_output = str_util.pretty_diff(
            expected_json,
            actual_json,
            diff_type=diff_type,
        )
        log.info(diff_output)
        log.info(f"--------------- DIFF ({diff_type}) END -----------------")

    def _log_table_diff(self, expected_json: str, actual_json: str):
        log.info("--------------- DIFF (table) BEGIN ---------------")
        table = RichConsoleDiff().build_table(
            expected_json.splitlines(keepends=True),
            actual_json.splitlines(keepends=True),
            fromdesc="expected",
            todesc="actual",
        )
        log.render(table)
        log.info("--------------- DIFF (table) END -----------------")


class TimingSink(BaseSink):
    def __init__(self, http_timing: bool = False):
        super().__init__()
        self.http_timing = http_timing
        self.run_started_ts: int = 0
        self.run_finished_ts: int = 0
        self.test_started_ts: dict[str, int] = {}
        self.test_totals_ms: dict[str, int] = {}
        self._last_step_event: dict[str, tuple[str, int]] = {}
        self.phase_durations_ms: dict[str, dict[str, int]] = defaultdict(dict)
        self.http_phase_durations_ms: dict[str, list[int]] = defaultdict(list)

    def install(self):
        self._connect(events.RUN_STARTED, self._on_run_started)
        self._connect(events.RUN_FINISHED, self._on_run_finished)

        self._connect(events.TEST_STARTED, self._on_test_started)
        self._connect(events.TEST_FINISHED, self._on_test_finished)
        self._connect(events.CREATE_TESTCASE, self._on_step_event)
        self._connect(events.CREATE_REQUEST, self._on_step_event)
        self._connect(events.EXECUTE_REQUEST, self._on_step_event)
        self._connect(events.HTTP_TRANSPORT, self._on_step_event)
        self._connect(events.HTTP_RESPONSE, self._on_step_event)
        self._connect(events.VERIFY_STATUS, self._on_step_event)
        self._connect(events.VERIFY_RESPONSE, self._on_step_event)
        self._connect(events.VERIFY_RESPONSE_HEADERS, self._on_step_event)
        return self

    def _test_key(self, kw: dict) -> str | None:
        return kw.get("test_id") or kw.get("testfile")

    def _on_run_started(self, _sender, **kw):
        self.run_started_ts = kw.get("ts", 0)

    def _on_run_finished(self, _sender, **kw):
        self.run_finished_ts = kw.get("ts", 0)
        total_ms = self.run_finished_ts - self.run_started_ts
        log.info(f"took={total_ms}ms")

    def _on_test_started(self, _sender, **kw):
        test_key = self._test_key(kw)
        ts = kw.get("ts")
        if test_key and isinstance(ts, int):
            self.test_started_ts[test_key] = ts

    def _on_step_event(self, _sender, **kw):
        test_key = self._test_key(kw)
        event_name = kw.get("event")
        ts = kw.get("ts")
        if not (test_key and event_name and isinstance(ts, int)):
            return

        previous = self._last_step_event.get(test_key)
        if previous is not None:
            previous_event, previous_ts = previous
            duration_ms = max(0, ts - previous_ts)
            self.phase_durations_ms[test_key][previous_event] = duration_ms
            if previous_event == events.HTTP_TRANSPORT:
                self.http_phase_durations_ms[test_key].append(duration_ms)

        self._last_step_event[test_key] = (event_name, ts)

    def _on_test_finished(self, _sender, **kw):
        test_key = self._test_key(kw)
        ts = kw.get("ts")
        if not (test_key and isinstance(ts, int)):
            return
        self._last_step_event.pop(test_key, None)
        start_ts = self.test_started_ts.pop(test_key, None)
        if start_ts is None:
            return
        total_ms = max(0, ts - start_ts)
        self.test_totals_ms[test_key] = total_ms

        prefix = ""
        http_label = "http"
        total_label = "took"
        timings = []

        if self.http_timing and self.http_phase_durations_ms.get(test_key):
            prefix = "•"
            total_label = "total\t"
            http_total = sum(self.http_phase_durations_ms[test_key])
            timings.append(f"[dim]{prefix}{http_label}\t {http_total}ms[/dim]")

        timings.append(f"[dim]{prefix}{total_label} {total_ms}ms[/dim]")

        log.info("\n".join(timings))

@dataclass
class SinkInstallation:
    sinks: list[BaseSink] = field(default_factory=list)
    console_sink: ConsoleOutputSink | None = None
    timing_sink: TimingSink | None = None

    def close(self):
        for sink in reversed(self.sinks):
            sink.close()


def install_runtime_sinks(conf: dict) -> SinkInstallation:
    installation = SinkInstallation()

    console_sink = ConsoleOutputSink(conf).install()

    installation.console_sink = console_sink
    installation.sinks.append(console_sink)

    if conf_get(conf, Settings.TIMING):
        timing_sink = TimingSink(http_timing=bool(conf_get(conf, Settings.HTTP_TIMING))).install()
        installation.timing_sink = timing_sink
        installation.sinks.append(timing_sink)

    return installation
