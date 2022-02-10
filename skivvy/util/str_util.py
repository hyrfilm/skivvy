import difflib
import json

RED_COLOR = '\033[91m\b'
GREEN_COLOR = '\033[92m\b'
RESET_COLOR = '\033[0m'


def diff_strings(a, b, colorize=True):
    difference = difflib.Differ()

    lines = difference.compare(a.splitlines(), b.splitlines())
    lines = [colorize_line(line, colorize) for line in lines]

    print("\n".join(lines))


def colorize_line(line, colorize):
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


def tojsonstr(o):
    return json.dumps(o, sort_keys=True, indent=2)