from __future__ import annotations

import time
import uuid
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

CREATE_TESTCASE = "test.create_testcase"
CREATE_REQUEST = "test.create_request"
EXECUTE_REQUEST = "test.execute_request"
HTTP_TRANSPORT = "test.http_transport"
HTTP_RESPONSE = "test.http_response"
VERIFY_STATUS = "test.verify_status"
VERIFY_RESPONSE = "test.verify_response"
VERIFY_RESPONSE_HEADERS = "test.verify_response_headers"

_ns = Namespace()


class RuntimeEventListener:
    def __init__(self):
        self.run_id: str | None = None
        self.test_id: str | None = None
        self.testfile: str | None = None
        self.seq = 0

    def reset(self):
        self.run_id = None
        self.test_id = None
        self.testfile = None
        self.seq = 0

    def before_emit(self, name: str, msg: dict[str, Any]):
        self.seq += 1
        msg.setdefault("seq", self.seq)

        if name == RUN_STARTED:
            self.test_id = None
            self.testfile = None

        if self.run_id is not None and "run_id" not in msg:
            msg["run_id"] = self.run_id
        if self.test_id is not None and "test_id" not in msg:
            msg["test_id"] = self.test_id
        if self.testfile is not None and "testfile" not in msg:
            msg["testfile"] = self.testfile

        if "run_id" in msg:
            self.run_id = msg["run_id"]

        if name == TEST_STARTED:
            if "test_id" not in msg and "testfile" in msg:
                msg["test_id"] = msg["testfile"]
            self.test_id = msg.get("test_id")
            self.testfile = msg.get("testfile")

    def after_emit(self, name: str):
        if name == TEST_FINISHED:
            self.test_id = None
            self.testfile = None
        if name == RUN_FINISHED:
            self.reset()


_runtime_listener = RuntimeEventListener()


def now_ms() -> int:
    return int(time.time() * 1000)


def new_run_id() -> str:
    return uuid.uuid4().hex


def signal(name: str):
    return _ns.signal(name)


def reset_runtime_listener():
    _runtime_listener.reset()


def emit(name: str, **payload):
    msg = dict(payload)
    _runtime_listener.before_emit(name, msg)
    msg.setdefault("ts", now_ms())
    try:
        return signal(name).send(None, event=name, **msg)
    finally:
        _runtime_listener.after_emit(name)
