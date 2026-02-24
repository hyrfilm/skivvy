from __future__ import annotations

import contextvars
import logging
import time
import uuid
from contextlib import contextmanager
from typing import Any, Callable

_logger = logging.getLogger(__name__)

try:
    from blinker import Namespace  # type: ignore
except ModuleNotFoundError:
    # Fallback for environments where blinker has not been installed yet.
    class _Signal:
        def __init__(self):
            self._receivers: list[Callable[..., Any]] = []

        def connect(self, receiver: Callable[..., Any]):
            if receiver not in self._receivers:
                self._receivers.append(receiver)
            return receiver

        def disconnect(self, receiver: Callable[..., Any]):
            self._receivers = [r for r in self._receivers if r is not receiver]

        def send(self, sender: object | None = None, **kwargs):
            results = []
            for receiver in list(self._receivers):
                results.append((receiver, receiver(sender, **kwargs)))
            return results

    class Namespace:  # type: ignore[override]
        def __init__(self):
            self._signals: dict[str, _Signal] = {}

        def signal(self, name: str) -> _Signal:
            if name not in self._signals:
                self._signals[name] = _Signal()
            return self._signals[name]


RUN_STARTED = "run.started"
TEST_STARTED = "test.started"
TEST_PASSED = "test.passed"
TEST_FAILED = "test.failed"
RUN_FINISHED = "run.finished"
TEST_PHASE_STARTED = "test.phase.started"
TEST_PHASE_FINISHED = "test.phase.finished"
TEST_PHASE_FAILED = "test.phase.failed"

_ns = Namespace()
_event_context: contextvars.ContextVar[dict[str, Any]] = contextvars.ContextVar(
    "skivvy_event_context", default={}
)


def now_ms() -> int:
    return int(time.time() * 1000)


def new_run_id() -> str:
    return uuid.uuid4().hex


def signal(name: str):
    return _ns.signal(name)


def current_context() -> dict[str, Any]:
    return dict(_event_context.get())


@contextmanager
def with_context(**kwargs):
    merged = current_context()
    merged.update({k: v for k, v in kwargs.items() if v is not None})
    token = _event_context.set(merged)
    try:
        yield merged
    finally:
        _event_context.reset(token)


def emit(name: str, **payload):
    msg = current_context()
    msg.update(payload)
    msg.setdefault("ts", now_ms())
    try:
        return signal(name).send(None, event=name, **msg)
    except Exception as e:
        # Receiver failures must not break the test run.
        _logger.debug("Event subscriber error for %s: %s", name, e, exc_info=True)
        return []


@contextmanager
def phase_span(phase_name: str, **payload):
    start = time.perf_counter()
    emit(TEST_PHASE_STARTED, phase=phase_name, **payload)
    try:
        yield
    except Exception as e:
        elapsed_ms = (time.perf_counter() - start) * 1000
        emit(
            TEST_PHASE_FAILED,
            phase=phase_name,
            elapsed_ms=elapsed_ms,
            error=str(e),
            error_type=type(e).__name__,
            **payload,
        )
        raise
    else:
        elapsed_ms = (time.perf_counter() - start) * 1000
        emit(TEST_PHASE_FINISHED, phase=phase_name, elapsed_ms=elapsed_ms, **payload)
