#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from copy import deepcopy

from rich.console import Console

from skivvy import events
from skivvy.skivvy import run
from skivvy.verify import is_matcher
from skivvy.util import log
from skivvy.util.icdiff2 import RichConsoleDiff
from skivvy.util.str_util import pretty_diff, tojsonstr


def _build_side_by_side_table(expected: object, actual: object, console: Console):
    differ = RichConsoleDiff(console=console)
    return differ.build_table(
        tojsonstr(expected).splitlines(),
        tojsonstr(actual).splitlines(),
        fromdesc="Expected",
        todesc="Actual",
    )


_OMIT = object()
_MISSING = "<missing>"
_OMITTED_MARKER_KEY = "__omitted_items__"
_LIST_COMPACT_ACTUAL_CHARS_THRESHOLD = 2000
_LIST_COMPACT_RATIO_THRESHOLD = 3
_LIST_SAMPLE_LIMIT = 4


def _is_matcher_string(value: object) -> bool:
    return isinstance(value, str) and is_matcher(value)


def _safe_json_len(value: object) -> int:
    try:
        return len(tojsonstr(value))
    except Exception:
        return len(str(value))


def _should_compact_list(expected: list, actual: list) -> bool:
    if len(actual) <= max(len(expected) + 2, _LIST_SAMPLE_LIMIT + 1):
        return False
    expected_len = max(_safe_json_len(expected), 1)
    actual_len = _safe_json_len(actual)
    return (
        actual_len >= _LIST_COMPACT_ACTUAL_CHARS_THRESHOLD
        and actual_len >= expected_len * _LIST_COMPACT_RATIO_THRESHOLD
    )


def _project_item_to_expected_surface(template: object, item: object) -> object:
    if isinstance(template, dict) and isinstance(item, dict):
        projected = {}
        for key, expected_value in template.items():
            projected[key] = item.get(key, _MISSING)
            # recurse only to keep nested expected surface, but do not omit equal values
            if key in item and isinstance(expected_value, dict) and isinstance(item[key], dict):
                projected[key] = _project_item_to_expected_surface(expected_value, item[key])
        return projected
    return item


def _compact_actual_list_against_expected(expected: list, actual: list) -> list:
    if not actual:
        return actual

    if len(expected) == 1:
        template = expected[0]
        sample = [_project_item_to_expected_surface(template, item) for item in actual[:_LIST_SAMPLE_LIMIT]]
    else:
        sample = []
        for idx, item in enumerate(actual[:_LIST_SAMPLE_LIMIT]):
            template = expected[min(idx, len(expected) - 1)]
            sample.append(_project_item_to_expected_surface(template, item))

    omitted = len(actual) - len(sample)
    if omitted > 0:
        sample.append({_OMITTED_MARKER_KEY: omitted, "total_items": len(actual)})
    return sample


def _prune_equal_within_expected_surface(expected: object, actual: object, compact_lists=True):
    # Preserve matcher expressions as-is; do not attempt semantic evaluation here.
    if _is_matcher_string(expected):
        return expected, actual

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


def _phase_aware_projected_diff_payload(payload: dict) -> tuple[object | None, object | None]:
    testfile = str(payload.get("testfile", ""))
    failures = _PHASE_FAILURES_BY_TEST.get(testfile, [])
    last_phase = failures[-1]["phase"] if failures else None
    expected = deepcopy(payload.get("expected"))
    actual = deepcopy(payload.get("actual"))

    if not isinstance(expected, dict) or not isinstance(actual, dict):
        return expected, actual

    if last_phase == "verify_status":
        return {"status": expected.get("status")}, {"status": actual.get("status")}

    if last_phase == "verify_response":
        expected_response = expected.get("response")
        actual_response = actual.get("response")
        pruned_expected, pruned_actual = _prune_equal_within_expected_surface(
            expected_response, actual_response
        )
        if pruned_expected is _OMIT:
            return {"response": "<no-diff>"} , {"response": "<no-diff>"}
        return {"response": pruned_expected}, {"response": pruned_actual}

    if last_phase == "verify_response_headers":
        return (
            {"response_headers": expected.get("response_headers")},
            {"response_headers": actual.get("response_headers")},
        )

    return expected, actual


_PHASE_FAILURES_BY_TEST: dict[str, list[dict]] = defaultdict(list)


def _collect_omitted_markers(value: object) -> list[dict]:
    found: list[dict] = []
    if isinstance(value, dict):
        if _OMITTED_MARKER_KEY in value:
            found.append(value)
        for v in value.values():
            found.extend(_collect_omitted_markers(v))
    elif isinstance(value, list):
        for item in value:
            found.extend(_collect_omitted_markers(item))
    return found


def _run_skivvy(cfg_file: str, passthrough_args: list[str], show_current_logs: bool) -> bool:
    old_argv = sys.argv
    try:
        effective_args = list(passthrough_args)
        if not show_current_logs and not any(arg.startswith("--set=log_level=") for arg in effective_args):
            effective_args.append("--set=log_level=CRITICAL")

        sys.argv = ["skivvy", cfg_file, *effective_args]
        return bool(run())
    finally:
        sys.argv = old_argv


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prototype helper: compare diff styles for each failing skivvy test."
    )
    parser.add_argument(
        "cfg_file",
        nargs="?",
        default="examples/typicode/failing.json",
        help="Skivvy config to run (default: examples/typicode/failing.json)",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=80,
        help="Console width used for side-by-side diff rendering",
    )
    parser.add_argument(
        "--show-current-logs",
        action="store_true",
        help="Keep skivvy's normal logging enabled while comparing diffs",
    )
    parser.add_argument(
        "--compact-mode",
        action="store_true",
        help=(
            "Prioritize phase-aware projected diffs and skip raw diff sections "
            "when heuristic list compaction is triggered"
        ),
    )
    parser.add_argument(
        "skivvy_args",
        nargs=argparse.REMAINDER,
        help="Additional args passed through to skivvy (prefix with --)",
    )
    args = parser.parse_args()

    if args.skivvy_args and args.skivvy_args[0] == "--":
        args.skivvy_args = args.skivvy_args[1:]

    if not args.show_current_logs:
        # This only affects startup logs before testcase config overrides are applied.
        log.set_default_level("CRITICAL")

    console = Console(width=args.width)
    seen_failures: list[str] = []

    def on_phase_failed(_sender, **payload):
        testfile = payload.get("testfile")
        if testfile:
            _PHASE_FAILURES_BY_TEST[str(testfile)].append(payload)

    def on_test_failed(_sender, **payload):
        testfile = str(payload.get("testfile", "<unknown>"))
        expected = payload.get("expected")
        actual = payload.get("actual")
        seen_failures.append(testfile)

        console.rule(f"[bold red]FAIL[/bold red] {testfile}")
        if _PHASE_FAILURES_BY_TEST.get(testfile):
            phases = ", ".join(p["phase"] for p in _PHASE_FAILURES_BY_TEST[testfile])
            console.print(f"[bold]Phase failures:[/bold] {phases}")

        if expected is None or actual is None:
            console.print("[yellow]No expected/actual payload available for diff[/yellow]")
            return
        
        projected_expected, projected_actual = _phase_aware_projected_diff_payload(payload)
        omitted_markers: list[dict] = []
        if projected_expected is not None and projected_actual is not None:
            omitted_markers = _collect_omitted_markers(projected_actual)
            if args.compact_mode:
                console.print("\n[bold]phase-aware projected diff (unified)[/bold]")
                console.print(
                    pretty_diff(
                        tojsonstr(projected_expected),
                        tojsonstr(projected_actual),
                        diff_type="unified",
                    )
                )
                console.print("\n[bold]phase-aware projected diff (side-by-side)[/bold]")
                console.print(_build_side_by_side_table(projected_expected, projected_actual, console))
            if omitted_markers:
                summaries = []
                for marker in omitted_markers:
                    summaries.append(
                        f"omitted {marker.get('__omitted_items__')} of {marker.get('total_items')} actual list items"
                    )
                console.print(
                    f"\n[bold yellow]heuristic compaction applied:[/bold yellow] {'; '.join(summaries)}"
                )
            if not args.compact_mode:
                console.print("\n[bold]phase-aware projected diff (unified)[/bold]")
                console.print(
                    pretty_diff(
                        tojsonstr(projected_expected),
                        tojsonstr(projected_actual),
                        diff_type="unified",
                    )
                )
                console.print("\n[bold]phase-aware projected diff (side-by-side)[/bold]")
                console.print(_build_side_by_side_table(projected_expected, projected_actual, console))

        skip_raw_diffs = args.compact_mode and bool(omitted_markers)
        if skip_raw_diffs:
            console.print(
                "\n[yellow]Skipping raw diff renderers in compact mode because heuristic compaction triggered.[/yellow]"
            )
            return

        console.print("\n[bold]pretty_diff (current default, ndiff)[/bold]")
        console.print(pretty_diff(tojsonstr(expected), tojsonstr(actual), diff_type="ndiff"))

        console.print("\n[bold]pretty_diff (unified)[/bold]")
        console.print(pretty_diff(tojsonstr(expected), tojsonstr(actual), diff_type="unified"))

        console.print("\n[bold]icdiff2-style side-by-side[/bold]")
        console.print(_build_side_by_side_table(expected, actual, console))

    phase_sig = events.signal(events.TEST_PHASE_FAILED)
    fail_sig = events.signal(events.TEST_FAILED)
    phase_sig.connect(on_phase_failed)
    fail_sig.connect(on_test_failed)
    try:
        _PHASE_FAILURES_BY_TEST.clear()
        ok = _run_skivvy(args.cfg_file, args.skivvy_args, args.show_current_logs)
    finally:
        phase_sig.disconnect(on_phase_failed)
        fail_sig.disconnect(on_test_failed)

    console.rule("[bold]Summary[/bold]")
    console.print(f"Config: {args.cfg_file}")
    console.print(f"Run result: {'PASS' if ok else 'FAIL'}")
    console.print(f"Failure diffs shown: {len(seen_failures)}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
