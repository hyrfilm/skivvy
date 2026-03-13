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
    h.setFormatter(logging.Formatter("%(message)s"))
    return h


_handler = _create_rich_handler()
_logger.setLevel(logging.INFO)
_logger.propagate = False
_logger.addHandler(_handler)


def _log(level, msg):
    if msg is None:
        return
    if not isinstance(msg, str):
        msg = str(msg)
    _logger.log(level, msg)


def debug(msg):
    _log(logging.DEBUG, msg)


def info(msg):
    _log(logging.INFO, msg)


def warning(msg):
    _log(logging.WARNING, msg)


def error(msg_or_err: Exception | str):
    _log(logging.ERROR, msg_or_err)


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


def log_at(level: int | str | None, msg):
    resolved = _resolve_level(level)
    if resolved is None:
        return
    _log(resolved, msg)


def set_default_level(level):
    _logger.setLevel(level)


def is_debug_enabled() -> bool:
    return _logger.isEnabledFor(logging.DEBUG)


def console_width() -> int:
    return _handler.console.width


def render(renderable) -> None:
    _handler.console.print(renderable)
