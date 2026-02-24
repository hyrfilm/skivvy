# Prototype: Diffing Experiments

## Goal

Compare diff styles on real failing skivvy examples and determine what actually improves debugging.

## Key Finding (Most Important)

Payload shaping matters more than the diff algorithm.

The biggest improvement came from:

1. removing noisy `response_headers` from generic failure diff payloads (prototype hack)
2. phase-aware diff projection (only diff the part that failed)
3. expected-surface pruning (omit equal fields inside the expected response surface)

## Key Files

- `scripts/compare_failure_diffs.py`
- `src/skivvy/skivvy.py` (prototype TODO hack removing response headers from `error_context`)
- `src/skivvy/util/icdiff2.py`
- `tests/test_event_diff_prototype.py`
- `examples/typicode/tests/failure/*.json`

## How To Run

- Default (real-world curated failures):
  - `just diff-examples examples/typicode/failing.json`
- Compact-first mode (better for huge list-heavy failures):
  - `just diff-examples-compact examples/typicode/failing.json`

This prints, for each failing testcase:

- `pretty_diff` (`ndiff`)
- `pretty_diff` (`unified`)
- `icdiff2` side-by-side
- phase-aware projected diff (`unified`)
- phase-aware projected diff (side-by-side)

In compact mode, projected diffs are shown first. If heuristic list compaction triggers, the script also skips the raw diff renderers (`ndiff`, raw `unified`, raw side-by-side) for that failure to avoid huge noisy output.

## Phase-Aware Projection (Prototype Behavior)

The script uses `test.phase.failed` to choose what to diff:

- `verify_status` -> diff only `status`
- `verify_response` -> diff only `response`, then recursively prune equal fields inside the expected surface
- `verify_response_headers` -> diff only headers (kept as a placeholder path for later)
- fallback -> diff the full expected/actual payloads

## Matcher-Aware Pruning Note

The projection logic preserves matcher strings (for example `"$between 10 20"`) and does not attempt to re-evaluate matcher semantics during pruning.

This is intentional for the prototype.

## Current Prototype Hacks / TODOs

- `src/skivvy/skivvy.py` currently excludes `response_headers` from `error_context` (TODO marked in code)
- This makes generic diffs much cleaner, but can break tests or tooling that expect headers in `error_context`
- Rich side-by-side tables are useful locally but still have layout issues (header spacer row + wrapping alignment for long strings)
- Large list failures use a quick heuristic compaction in projected diffs:
  - when `actual` is much larger than `expected`, only a small projected sample is shown
  - an omitted-items marker is appended (for example `{"__omitted_items__": 4996, "total_items": 5000}`)
  - the script prints an explicit `heuristic compaction applied` note when this happens

## Renderer Opinions (Based On Real Examples)

- `unified` looks strongest as the likely default textual diff
- `ndiff` is useful for tiny/intraline diffs but gets noisy quickly
- Rich side-by-side is very useful locally, especially after phase-aware projection

## New Failure Examples Added For Matcher Comparison

Additional real-world matcher failure cases were added under `examples/typicode/tests/failure/`:

- `$between` on `id`
- `$contains` on `title`
- `$regexp` on `email`
- `$text` on `name`
- `$len` on `title`

These are intended to produce varied failure shapes when running the diff comparison script.
