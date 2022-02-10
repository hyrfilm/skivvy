import logging

import sys


def get_logger(name, level=logging.INFO):
    # let's just use one handler for now
    # if we use a stderr handler a message will sent to both
    # pipes when an error code occurs
    # this is because there's no way to set a range
    # for a handler's log level. Eg "emit only debug & info"

    # anyway, when we had a stderr handler text
    # was duplicated in the terminal in an annoying way
    # there's probably some way around this that I haven't found,,,

    logger = logging.getLogger(name)
    default_handler = logging.StreamHandler(sys.stdout)
    default_handler.setLevel(logging.DEBUG)
    logger.addHandler(default_handler)
    logger.setLevel(level)

    # error_handler = logging.StreamHandler(sys.stderr)
    # error_handler.setLevel(logging.WARNING)
    # logger.addHandler(error_handler)
    return logger
