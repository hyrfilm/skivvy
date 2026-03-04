import logging

from rich.console import Console
from rich.logging import RichHandler

_logger = logging.getLogger(__name__)

def _create_rich_handler():
    console = Console()
    h = RichHandler(
        console=console,
        show_time=False,
        show_path=False,
        markup=True,
        show_level=False,
        rich_tracebacks=True,
    )
    h.terminator = ""  # important for your layout
    h.setFormatter(logging.Formatter("%(message)s"))
    return h


_handler = _create_rich_handler()
_logger.setLevel(logging.INFO)
_logger.propagate = False
_logger.addHandler(_handler)


def _log(level, msg, new_line=True):
    if msg is None:
        return
    if not isinstance(msg, str):
        msg = str(msg)
    if new_line and not msg.endswith("\n"):
        msg += "\n"
    _logger.log(level, msg)


def debug(msg, new_line=True):
    _log(logging.DEBUG, msg, new_line)


def info(msg, new_line=True):
    _log(logging.INFO, msg, new_line)


def warning(msg, new_line=True):
    _log(logging.WARNING, msg, new_line)


def error(msg_or_err: Exception | str, new_line=True):
    _log(logging.ERROR, msg_or_err, new_line)


def _resolve_level(level: int | str | None):
    if level is None:
        return None
    if isinstance(level, int):
        return level
    if not isinstance(level, str):
        raise ValueError(f"Unsupported log level value: {level!r}")

    normalized = level.strip().upper()
    if normalized in {"", "NONE", "NULL", "OFF", "FALSE"}:
        return None
    if normalized.lstrip("-").isdigit():
        return int(normalized)

    resolved = logging.getLevelNamesMapping().get(normalized)
    if resolved is None:
        raise ValueError(f"Unknown log level: {level!r}")
    return resolved


def log_at(level: int | str | None, msg, new_line=True):
    resolved = _resolve_level(level)
    if resolved is None:
        return
    _log(resolved, msg, new_line)


def set_default_level(level):
    _logger.setLevel(level)


def is_debug_enabled() -> bool:
    return _logger.isEnabledFor(logging.DEBUG)


def render(renderable) -> None:
    console = getattr(_handler, "console", None)
    if console is None:
        _log(logging.INFO, str(renderable), new_line=True)
        return
    console.print(renderable)
