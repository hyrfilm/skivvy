import matchers
from util import log_util
from util.str_util import tojsonstr

_logger = log_util.get_logger(__name__)

# basically just looks at a string and the name of a matcher and determines if the string is invoking that matcher
# returns true in that case, false otherwise
def has_matcher_syntax(expected, matcher):
    # TODO: not compatible with python 3 - FIX
    try:
        first_word = expected.split()[0]
        if isinstance(expected, basestring) and first_word == matcher:
            return True
        return False
    except:
        return False


def is_matcher(expected):
    for matcher in matchers.matcher_dict.keys():
        if has_matcher_syntax(expected, matcher):
            return True
    return False


def verify_dict(expected, actual, **match_options):
    for key in expected.keys():
        _logger.debug("Checking '%s'..." % key)
        verify(expected.get(key), actual.get(key), **match_options)
        _logger.debug("Success.")


# TODO: we should support strict or non-strict types of comparisons of lists
def verify_list(expected, actual, **match_options):
    match_subsets = match_options.get("match_subsets", False)

    for expected_entry in expected:
        _logger.debug("Checking '%s'..." % expected_entry)
        if expected_entry not in actual:
            if match_subsets:
                verify_list_subset(expected_entry, actual, **match_options)
            else:
                raise Exception("Didn't find:\n%s\nin:\n%s" % (tojsonstr(expected_entry), tojsonstr(actual)))


def verify_list_subset(expected_entry, actual, **match_options):
    if isinstance(actual, list):
        for actual_entry in actual:
            if isinstance(actual_entry, dict) and isinstance(expected_entry, dict):
                e = dict(expected_entry)
                a = dict(actual_entry)

                a.update(e)

                try:
                    verify(a, actual_entry, **match_options)
                    return
                except:
                    pass

    raise Exception("Didn't find:\n%s\nin:\n%s" % (tojsonstr(expected_entry), tojsonstr(actual)))


def verify_matcher(expected, actual):
    for matcher in matchers.matcher_dict.keys():
        if has_matcher_syntax(expected, matcher):
            expected = expected[len(matcher):]
            matcher_func = matchers.matcher_dict.get(matcher)
            result, msg = matcher_func(expected, actual)
            if not result:
                raise Exception(msg)

    return matchers.default_matcher(expected, actual)


def verify(expected, actual, **match_options):
    if is_matcher(expected):
        verify_matcher(expected, actual)
    elif type(expected) != type(actual):
        if not actual and not expected:
            if match_options.get("match_falsiness"):
                return True
        raise Exception("%s is not the same type as %s" % (expected, actual))
    elif isinstance(expected, dict):
        return verify_dict(expected, actual, **match_options)
    elif isinstance(expected, list):
        return verify_list(expected, actual, **match_options)
    elif expected != actual:
        raise Exception("expected %s but was %s" % (expected, actual))
    else:
        return True
