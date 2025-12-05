import difflib
import json
import re
from functools import cache, partial
from typing import AnyStr


def _colorize_diff(diff_text: str) -> str:
    """
    Lightweight markup-based coloring for diff output when Rich rendering
    isn't available. Uses red for removals, green for additions, yellow for
    inline hints, and dim for unchanged/context lines.
    """
    lines = []
    for line in diff_text.splitlines():
        if line.startswith("+"):
            lines.append(f"[green]{line}[/green]")
        elif line.startswith("-"):
            lines.append(f"[red]{line}[/red]")
        elif line.startswith("?"):
            lines.append(f"[yellow]{line}[/yellow]")
        elif line.startswith("@@") or line.startswith(("***", "---", "+++")):
            lines.append(f"[cyan]{line}[/cyan]")
        else:
            lines.append(f"[dim]{line}[/dim]")

    # Preserve trailing newline, if any
    trailing = "\n" if diff_text.endswith("\n") else ""
    return "\n".join(lines) + trailing


def pretty_diff(
    expected: str,
    actual: str,
    diff_type: str = "ndiff",
    lines: int = 3,
) -> str:
    """
    Diff two JSON strings using a chosen diff type.

    Parameters:
        expected (str): First JSON string
        actual (str): Second JSON string
        diff_type (str): "unified", "context", or "ndiff"
        lines (int): Number of context lines for unified/context

    Returns:
        str: The diff as a string.
    """
    try:
        obj1 = json.loads(expected)
    except Exception as _e:
        obj1 = str(expected)

    try:
        obj2 = json.loads(actual)
    except Exception as _e:
        obj2 = str(actual)


    # Convert objects to pretty, stable JSON lines for diffing
    j1 = json.dumps(obj1, indent=2, sort_keys=True).splitlines(keepends=True)
    j2 = json.dumps(obj2, indent=2, sort_keys=True).splitlines(keepends=True)

    def _raw_diff() -> str:
        if diff_type == "unified":
            diff_iter = difflib.unified_diff(j1, j2, fromfile=expected, tofile=actual, n=lines)
        elif diff_type == "context":
            diff_iter = difflib.context_diff(j1, j2, fromfile=expected, tofile=actual, n=lines)
        else:  # ndiff
            diff_iter = difflib.ndiff(j1, j2)
        return "".join(diff_iter)
    return _colorize_diff(_raw_diff())


def stylize(s):
    for name, value in tags.items():
        s = s.replace(value)
    return s

def tojsonstr(o):
    return json.dumps(o, sort_keys=True, indent=2)


def coerce_str_to_int(s):
    try:
        return int(s)
    except ValueError:
        return s


def matches_any(s, patterns):
    for p in patterns:
        if p.match(s):
            return True
    return False

@cache
def compile_regexp(regexp: str) -> re.Pattern[AnyStr]:
    return re.compile(regexp)

def compile_regexps(regexps):
    return [re.compile(".*" + p) for p in regexps]

def _default_done(results, variable_name):
    match results:
        # success: one single source for the variable was found, return the value
        case [value]:
            return value
        # ambiguous failure: more than one source for the variable was found
        case [head, *tail]:
            tail.insert(0, head)
            raise ValueError(f"Multiple variable declarations for {variable_name}: {list(tail)}")
        case _:
            raise ValueError(f"Missing variable definition: {variable_name}")

def replacer(match, resolve_funcs, done_func):
    variable_name = match.group(1)
    assert variable_name is not None # should never happen
    results = [func(variable_name) for func in resolve_funcs]
    results = [str(r) for r in results if r is not None]
    return done_func(results, variable_name)

def expand_string(s, pattern, resolve_funcs, done_func=_default_done):
    replace_func = partial(replacer, resolve_funcs=resolve_funcs, done_func=done_func)
    return pattern.sub(replace_func, s)
