import matchers
from util import log_util
_logger = log_util.get_logger(__name__)

def has_matcher_syntax(expected, matcher):
    # TODO: not compatible with python 3 - FIX
    if isinstance(expected, basestring) and expected.startswith(matcher):
        return True
    return False


def is_matcher(expected):
    for matcher in matchers.matcher_dict.keys():
        if has_matcher_syntax(expected, matcher):
            return True
    return False


def verify_dict(expected, actual):
    for key in expected.keys():
        _logger.debug("Checking '%s'..." % key)
        verify(expected.get(key), actual.get(key))
        _logger.debug("Success.")


# TODO: we should support strict or non-strict types of comparsions of lists
def verify_list(expected, actual):
    for el in expected:
        _logger.debug("Checking '%s'..." % el)
        if el not in actual:
            raise Exception("Didn't find '%s' in %s" % (el, actual))


def verify_matcher(expected, actual):
    for matcher in matchers.matcher_dict.keys():
        if has_matcher_syntax(expected, matcher):
            expected = expected[len(matcher):]
            matcher_func = matchers.matcher_dict.get(matcher)
            result, msg = matcher_func(expected, actual)
            if not result:
                raise Exception(msg)

    return matchers.default_matcher(expected, actual)


def verify(expected, actual):
    if is_matcher(expected):
        verify_matcher(expected, actual)
    elif type(expected) != type(actual):
        raise Exception("%s is not the same type as %s" % (expected, actual))
    elif isinstance(expected, dict):
        return verify_dict(expected, actual)
    elif isinstance(expected, list):
        return verify_list(expected, actual)
    elif expected != actual:
        raise Exception("expected %s but was %s" % (expected, actual))
    else:
        return True

