import logging
import sys
from contextlib import contextmanager

from rich.console import Console
from rich.logging import RichHandler

_logger = logging.getLogger(__name__)

def _create_plain_handler():
    h = logging.StreamHandler(sys.stdout)
    h.terminator = ""
    h.setFormatter(logging.Formatter("%(message)s"))
    return h


def _create_rich_handler():
    console = Console()
    h = RichHandler(
        console=console,
        show_time=False,
        show_path=False,
        markup=True,
    )
    h.terminator = ""  # important for your layout
    h.setFormatter(logging.Formatter("%(message)s"))
    return h

_handler = _create_rich_handler()
_logger.setLevel(logging.INFO)
_logger.propagate = False
_logger.addHandler(_handler)
_max_col_width = 80

# Per-test buffer (None if we're not in a test context)
_current_test_buffer = None

def _log(level, msg, new_line=True):
    if new_line and not msg.endswith("\n"):
        msg += "\n"
    _logger.log(level, msg)


def _buffer_or_log(level, msg, new_line=True):
    """If inside a testcase, buffer log entries; otherwise log immediately."""
    global _current_test_buffer

    if _current_test_buffer is not None:
        # store message *without* newline, and the level
        _current_test_buffer.append((level, msg, new_line))
    else:
        _log(level, msg, new_line)


def debug(msg, new_line=True):
    _buffer_or_log(logging.DEBUG, msg, new_line)


def info(msg, new_line=True):
    _buffer_or_log(logging.INFO, msg, new_line)


def warning(msg, new_line=True):
    _buffer_or_log(logging.WARNING, msg, new_line)


def error(msg, new_line=True):
    _buffer_or_log(logging.ERROR, msg, new_line)


def set_default_level(level):
    _logger.setLevel(level)


def adjust_col_width(strings):
    if not strings:
        return
    global _max_col_width
    max_width = max(len(s) for s in strings)
    _max_col_width = max_width + 4


def _format_test_prefix(testcase):
    return testcase.ljust(_max_col_width)


class _TestLogContext:
    def __init__(self, name):
        self.name = name
        self.ok = True  # caller flips this to False with ctx.fail()

    def fail(self):
        self.ok = False


@contextmanager
def testcase_logger(testcase_name: str):
    """
    Context manager to:
      - buffer ALL log calls (debug/info/warning/error) during a testcase
      - on exit, print "<testcase> OK/FAILED"
      - then print buffered lines in their original order
        (debug only if DEBUG is enabled)
    """
    global _current_test_buffer

    prev_buffer = _current_test_buffer
    buf = []
    _current_test_buffer = buf

    ctx = _TestLogContext(testcase_name)
    try:
        yield ctx
    finally:
        status = "[green]OK[/green]" if ctx.ok else "[blink][red]FAILED[/red][/blink]"
        # 1) main summary line
        _log(logging.INFO, f"{_format_test_prefix(testcase_name)} {status}")

        # 2) replay buffered log entries
        if buf:
            # Optional blank line between summary and details
            _log(logging.INFO, "")  # prints just "\n"

            for level, msg, new_line in buf:
                # Skip debug if logger isn't in DEBUG mode
                if level == logging.DEBUG and not _logger.isEnabledFor(logging.DEBUG):
                    continue
                _log(level, msg, new_line)

        _current_test_buffer = prev_buffer
