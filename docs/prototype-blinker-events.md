# Prototype: Blinker Events

## Goal

Prototype an event-driven lifecycle for skivvy without replacing current logging/output yet.

This branch keeps current behavior and emits structured events in parallel so we can:

- test logging-like behavior without asserting on terminal strings
- classify failures by phase
- measure timing
- experiment with alternate renderers / summaries

## Key Files

- `src/skivvy/events.py`
- `src/skivvy/skivvy.py`
- `src/skivvy/util/http_util.py`
- `tests/test_event_diff_prototype.py`

## Event Names (current prototype)

- `run.started`
- `test.started`
- `test.passed`
- `test.failed`
- `run.finished`
- `test.phase.started`
- `test.phase.finished`
- `test.phase.failed`

## Why Phase Events Exist

A single `test.failed` event is too coarse. We want to know where failure happened.

Current phase instrumentation wraps:

- `create_testcase`
- `create_request`
- `http_execute`
- `http_transport` (inside `http_util.do_request`)
- `verify_status`
- `verify_response`
- `verify_response_headers`

This lets subscribers do phase-aware behavior (for example diffing only `status` for status failures).

## Current Prototype Properties

- Synchronous delivery (intentionally fine: skivvy is explicitly non-concurrent)
- Event payload includes contextual fields (via `events.with_context`)
- Subscriber exceptions are caught in `events.emit(...)` to avoid breaking the run

## Known Caveats / TODOs

- If one Blinker subscriber raises, later subscribers for that same signal may not run (Blinker stops dispatch before our outer catch)
- `run.finished` is emitted only on normal `run()` completion
- Current logging still exists and still buffers via `log.testcase_logger(...)`
- No dedicated subscriber ordering API yet (registration order effectively matters)

## Useful Commands

- Run real failing examples while inspecting event-driven diff output:
  - `just diff-examples examples/typicode/failing.json`

## Notes For Future “Real PR”

- Keep events payloads structured (objects), not pre-rendered strings
- Add small subscriber modules (terminal logging, summary, timing)
- Add explicit tests for event ordering and subscriber-failure isolation
