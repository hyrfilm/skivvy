import difflib
import json
import re
from functools import cache, partial
from typing import AnyStr

RED_COLOR = '\033[91m\b'
GREEN_COLOR = '\033[92m\b'
RESET_COLOR = '\033[0m'

RESET_ALL = "\033[0m"
BOLD_ON, BOLD_OFF = "\033[1m",  "\033[22m"
UL_ON,   UL_OFF   = "\033[4m",  "\033[24m"
FG_RESET = "\033[39m"

tags = {
    "<b>": BOLD_ON, "</b>": BOLD_OFF,
    "<u>": UL_ON, "</u>": UL_OFF,
}

def diff_strings(a, b, colorize=True):
    difference = difflib.Differ()

    lines = difference.compare(a.splitlines(), b.splitlines())
    lines = [colorize_diff_line(line, colorize) for line in lines]

    return "\n".join(lines)


def colorize_diff_line(line, colorize):
    if not colorize:
        return line

    line_color = ""
    if line.startswith("?"):
        if "+" in line:
            line_color = GREEN_COLOR
        elif "-" in line:
            line_color = RED_COLOR
    elif line.startswith("-"):
        line_color = RED_COLOR
    return line_color + line + RESET_COLOR


def colorize(s, color):
    return color + s + RESET_COLOR

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
    results = [r for r in results if r is not None]
    return done_func(results, variable_name)

def expand_string(s, pattern, resolve_funcs, done_func=_default_done):
    replace_func = partial(replacer, resolve_funcs=resolve_funcs, done_func=done_func)
    return pattern.sub(replace_func, s)
