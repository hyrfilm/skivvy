import logging

import sys
from logging import DEBUG, INFO, WARNING, ERROR

_logger = logging.getLogger()
_handler = logging.StreamHandler(sys.stdout)
_logger.addHandler(_handler)
_handler.terminator = ''

def debug(s, new_line=True):
    _log(DEBUG, s, new_line)

def info(s, new_line=True):
    _log(INFO, s, new_line)

def warning(s, new_line=True):
    _log(WARNING, s, new_line)

def warn(s, new_line=True):
    warning(s, new_line)

def error(s, new_line=True):
    _log(ERROR, s, new_line)

def _log(level, s, new_line=True):
    _logger.log(level, s)
    if new_line:
        _logger.log(level, "\n")
    _handler.flush()

def set_default_level(log_level):
    _logger.setLevel(log_level)
