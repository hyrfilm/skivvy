from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Callable

from . import events
from .util import log


Disconnect = Callable[[], None]


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


class TerminalLifecycleSink(BaseSink):
    def __init__(self, renderer: str = "plain"):
        super().__init__()
        self.renderer = renderer

    def install(self):
        self._connect(events.RUN_STARTED, self._on_run_started)
        self._connect(events.RUN_PASSED, self._on_run_passed)
        self._connect(events.RUN_FAILED, self._on_run_failed)
        self._connect(events.RUN_FINISHED, self._on_run_finished)
        self._connect(events.TEST_STARTED, self._on_test_started)
        self._connect(events.TEST_PASSED, self._on_test_passed)
        self._connect(events.TEST_FAILED, self._on_test_failed)
        return self

    def _prefix(self) -> str:
        return "[dim]event[/dim]" if self.renderer == "rich" else "event"

    def _on_run_started(self, _sender, **kw):
        log.info(
            f"{self._prefix()} run.started tests={kw.get('test_count')}",
        )

    def _on_run_passed(self, _sender, **kw):
        log.info(f"{self._prefix()} run.passed tests={kw.get('num_tests')}")

    def _on_run_failed(self, _sender, **kw):
        log.info(
            f"{self._prefix()} run.failed failures={kw.get('failures')}/{kw.get('num_tests')}"
        )

    def _on_run_finished(self, _sender, **kw):
        log.info(
            f"{self._prefix()} run.finished success={kw.get('success')} elapsed_ms={kw.get('elapsed_ms')}"
        )

    def _on_test_started(self, _sender, **kw):
        log.info(f"{self._prefix()} test.started {kw.get('testfile')}")

    def _on_test_passed(self, _sender, **kw):
        log.info(f"{self._prefix()} test.passed {kw.get('testfile')}")

    def _on_test_failed(self, _sender, **kw):
        log.info(f"{self._prefix()} test.failed {kw.get('testfile')}")


class ErrorSink(BaseSink):
    """Experimental failure-event sink.

    TODO: Replace legacy direct failure diff logging with sink-driven rendering once the
    final config design (logging/timing/diffs) is decided.
    """

    def __init__(self, renderer: str = "plain"):
        super().__init__()
        self.renderer = renderer

    def install(self):
        self._connect(events.TEST_FAILED, self._on_test_failed)
        return self

    def _on_test_failed(self, _sender, **kw):
        err_context = kw.get("error_context") or {}
        failed_phase = err_context.get("failed_phase")
        if failed_phase:
            prefix = "[dim]error[/dim]" if self.renderer == "rich" else "error"
            log.info(f"{prefix} failed_phase={failed_phase}")


class TimingSink(BaseSink):
    def __init__(self, http_timing: bool = False):
        super().__init__()
        self.http_timing = http_timing
        self.test_started_ts: dict[str, int] = {}
        self.test_totals_ms: dict[str, int] = {}
        self._phase_started_ts: dict[tuple[str, str], int] = {}
        self.phase_durations_ms: dict[str, dict[str, int]] = defaultdict(dict)
        self.http_phase_durations_ms: dict[str, list[int]] = defaultdict(list)

    def install(self):
        self._connect(events.TEST_STARTED, self._on_test_started)
        self._connect(events.TEST_FINISHED, self._on_test_finished)
        self._connect(events.TEST_PHASE_STARTED, self._on_phase_started)
        self._connect(events.TEST_PHASE_FINISHED, self._on_phase_finished)
        self._connect(events.TEST_PHASE_FAILED, self._on_phase_finished)
        return self

    def _test_key(self, kw: dict) -> str | None:
        return kw.get("test_id") or kw.get("testfile")

    def _on_test_started(self, _sender, **kw):
        test_key = self._test_key(kw)
        ts = kw.get("ts")
        if test_key and isinstance(ts, int):
            self.test_started_ts[test_key] = ts

    def _on_phase_started(self, _sender, **kw):
        test_key = self._test_key(kw)
        phase = kw.get("phase")
        ts = kw.get("ts")
        if test_key and phase and isinstance(ts, int):
            self._phase_started_ts[(test_key, phase)] = ts

    def _on_phase_finished(self, _sender, **kw):
        test_key = self._test_key(kw)
        phase = kw.get("phase")
        ts = kw.get("ts")
        if not (test_key and phase and isinstance(ts, int)):
            return
        start_ts = self._phase_started_ts.pop((test_key, phase), None)
        if start_ts is None:
            return
        duration_ms = max(0, ts - start_ts)
        self.phase_durations_ms[test_key][phase] = duration_ms
        if phase == "http_transport":
            self.http_phase_durations_ms[test_key].append(duration_ms)

    def _on_test_finished(self, _sender, **kw):
        test_key = self._test_key(kw)
        ts = kw.get("ts")
        if not (test_key and isinstance(ts, int)):
            return
        start_ts = self.test_started_ts.pop(test_key, None)
        if start_ts is None:
            return
        total_ms = max(0, ts - start_ts)
        self.test_totals_ms[test_key] = total_ms
        log.info(f"[dim]timing[/dim] {test_key} total={total_ms}ms")
        if self.http_timing and self.http_phase_durations_ms.get(test_key):
            http_total = sum(self.http_phase_durations_ms[test_key])
            log.info(
                f"[dim]timing[/dim] {test_key} http_transport_total={http_total}ms"
            )


@dataclass
class SinkInstallation:
    sinks: list[BaseSink] = field(default_factory=list)
    terminal_sink: TerminalLifecycleSink | None = None
    error_sink: ErrorSink | None = None
    timing_sink: TimingSink | None = None

    def close(self):
        for sink in reversed(self.sinks):
            sink.close()


def install_runtime_sinks(conf: dict) -> SinkInstallation:
    """Install internal sinks for experimental event-driven output/timing.

    TODO: Replace temporary underscore flags with a stable logging/timing/diffs config
    schema once we finish comparing output approaches.
    TODO: Consider exposing a public sink registry/config after the design converges.
    """

    installation = SinkInstallation()

    rich_key_present = "_rich" in conf
    if rich_key_present:
        renderer = "rich" if bool(conf.get("_rich", False)) else "plain"
        terminal_sink = TerminalLifecycleSink(renderer=renderer).install()
        error_sink = ErrorSink(renderer=renderer).install()
        installation.terminal_sink = terminal_sink
        installation.error_sink = error_sink
        installation.sinks.extend([terminal_sink, error_sink])

    if bool(conf.get("_timing", False)):
        timing_sink = TimingSink(http_timing=bool(conf.get("_http_timing", False))).install()
        installation.timing_sink = timing_sink
        installation.sinks.append(timing_sink)

    return installation
