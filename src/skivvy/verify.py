from skivvy.skivvy_config2 import Settings
from skivvy.util import scope
from . import matchers
from .util import log
from .util.str_util import tojsonstr


# basically just looks at a string and the name of a matcher and determines if the string is invoking that matcher
# returns true in that case, false otherwise
def has_matcher_syntax(expected, matcher):
    try:
        first_word = expected.split()[0]
        if isinstance(expected, str) and first_word == matcher:
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
        log.debug("Checking '%s'..." % key)
        verify(expected.get(key), actual.get(key), **match_options)
        log.debug("Success.")


# TODO: support strict or non-strict types of comparisons of lists
def verify_list(expected, actual, **match_options):
    match_subsets = match_options.get("match_subsets", False)
    match_every_entry = match_options.get(Settings.MATCH_EVERY_ENTRY.key, False)

    for expected_entry in expected:
        log.debug("Checking '%s'..." % expected_entry)

        if match_every_entry:
            # Every actual entry must satisfy this expected template.
            if isinstance(actual, list):
                for actual_entry in actual:
                    _verify_entry(expected_entry, actual_entry, **match_options)
            continue

        if expected_entry in actual:
            continue  # fast path: exact Python equality

        # Matcher-aware search: try each actual entry using verify() semantics.
        # When match_subsets is true and both sides are dicts, use partial matching:
        # overlay expected keys onto actual so only expected keys are checked.
        found = False
        if isinstance(actual, list):
            for actual_entry in actual:
                try:
                    _verify_entry(expected_entry, actual_entry, **match_options)
                    found = True
                    break
                except Exception:
                    pass

        if not found:
            raise Exception(
                "Didn't find:\n%s\nin:\n%s"
                % (tojsonstr(expected_entry), tojsonstr(actual))
            )


def _verify_entry(expected_entry, actual_entry, **match_options):
    """Verify a single expected entry against a single actual entry.
    With match_subsets and both sides being dicts, only expected keys are checked."""
    match_subsets = match_options.get("match_subsets", False)
    if (
        match_subsets
        and isinstance(expected_entry, dict)
        and isinstance(actual_entry, dict)
    ):
        merged = {**actual_entry, **expected_entry}
        verify(merged, actual_entry, **match_options)
    else:
        verify(expected_entry, actual_entry, **match_options)


def verify_matcher(expected, actual):
    for matcher in matchers.matcher_dict.keys():
        if has_matcher_syntax(expected, matcher):
            expected = expected[len(matcher) :]
            matcher_func = matchers.matcher_dict.get(matcher)
            result, msg = matcher_func(expected, actual)
            if not result:
                raise Exception(msg)

    return matchers.default_matcher(expected, actual)


def verify(expected, actual, **match_options):
    validate_variable_names = match_options.get(
        Settings.VALIDATE_VARIABLE_NAMES.key, True
    )
    scope.set_validate_variable_names(validate_variable_names)
    matchers.set_matcher_options(match_options.get(Settings.MATCHER_OPTIONS.key, {}))
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
