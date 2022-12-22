import difflib
import json
import re

RED_COLOR = '\033[91m\b'
GREEN_COLOR = '\033[92m\b'
RESET_COLOR = '\033[0m'


def diff_strings(a, b, colorize=True):
    difference = difflib.Differ()

    lines = difference.compare(a.splitlines(), b.splitlines())
    lines = [colorize_diff_line(line, colorize) for line in lines]

    print("\n".join(lines))


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


def compile_regexps(regexps):
    return [re.compile(".*" + p) for p in regexps]
