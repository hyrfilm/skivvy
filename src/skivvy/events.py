from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from typing import Any

from blinker import Namespace

RUN_STARTED = "run.started"
RUN_PASSED = "run.passed"
RUN_FAILED = "run.failed"
RUN_FINISHED = "run.finished"

TEST_STARTED = "test.started"
TEST_PASSED = "test.passed"
TEST_FAILED = "test.failed"
TEST_FINISHED = "test.finished"

TEST_PHASE_STARTED = "test.phase.started"
TEST_PHASE_PASSED = "test.phase.passed"
TEST_PHASE_FAILED = "test.phase.failed"
TEST_PHASE_FINISHED = "test.phase.finished"

_ns = Namespace()
_context: dict[str, Any] = {}


def now_ms() -> int:
    return int(time.time() * 1000)


def new_run_id() -> str:
    return uuid.uuid4().hex


def signal(name: str):
    return _ns.signal(name)


def current_context() -> dict[str, Any]:
    return dict(_context)


@contextmanager
def with_context(**kwargs):
    previous = dict(_context)
    _context.update({k: v for k, v in kwargs.items() if v is not None})
    try:
        yield _context
    finally:
        _context.clear()
        _context.update(previous)


def emit(name: str, **payload):
    msg = current_context()
    msg.update(payload)
    msg.setdefault("ts", now_ms())
    # TODO: Revisit per-sink fatal vs isolated failure behavior after sink architecture stabilizes.
    return signal(name).send(None, event=name, **msg)


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
        emit(TEST_PHASE_PASSED, phase=phase_name, elapsed_ms=elapsed_ms, **payload)
        emit(TEST_PHASE_FINISHED, phase=phase_name, elapsed_ms=elapsed_ms, **payload)
