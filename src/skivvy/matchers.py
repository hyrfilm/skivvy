"""Built-in matchers used by skivvy"""
# coding=utf-8
import string
import re
import os.path
from datetime import datetime
from math import fabs

import requests

from skivvy.util.scope import has,fetch, store, get_current_namespace
from skivvy.util.str_util import coerce_str_to_int, compile_regexp
from skivvy.util import file_util, str_util
from skivvy.util import log
from skivvy.util import scope

DEFAULT_APPROXIMATE_THRESHOLD = 0.05  # default margin of error for a ~value to still be considered equal to another
SUCCESS_MSG = "OK"
STORE = {}

def strip_matcher_prefix(s):
    if s.startswith("$"):
        return s[1:]
    else:
        return s


def match_expression(expected, actual):
    result = eval(expected, {}, {"actual": actual})
    if result is True:
        return True, SUCCESS_MSG
    else:
        return False, "Expected '%s' to evaluate to True but was evaluated to False" % actual


def match_regexp(expected, actual):
    try:
        expected, actual = expected.strip(), str(actual)
        log.debug("Comparing '%s' to regexp: '%s'" % (actual, expected))
        if re.match(expected, actual):
            log.debug("It's a match.")
            return True, SUCCESS_MSG
        else:
            return False, "Expected '%s' to match regular expression '%s' - but didn't" % (actual, expected)
    except re.PatternError as e:
        return False, "Invalid regular expression pattern in testcase: %s - %s" % (expected, str(e))
    except Exception as e:
        return False, "Error when parsing: %s" % (str(e))


def match_valid_url(expected, actual):
    try:
        # we allow relative urls using the format "$valid_url /some_url prefix example.com" -> example.com/some_url
        relative_url = expected.split("prefix")
        if len(relative_url) == 2:
            prefix = relative_url[-1]
            prefix = prefix.strip()
            actual = prefix + actual

        valid_status_codes = [200]
        log.debug("Making request to %s" % actual)
        response = requests.get(actual, verify=False)
        if response.status_code in valid_status_codes:
            log.debug("Success.")
            return True, SUCCESS_MSG
        else:
            log.debug("Failure.")
            return False, "Expected %s but got %s" % (valid_status_codes, actual)
    except Exception as e:
        log.debug("Failure.")
        log.debug("http call failed for: %s" % actual)
        log.debug("expected: %s" % expected)
        return False, "Failed to make request to %s: %s" % (actual, e)


def match_text(expected, actual):
    if not actual:
        return False, "Expected %s but got %s" % (expected, actual)

    for c in actual:
        if c not in string.ascii_letters:
            return False, "Expected %s but got %s" % (expected, actual)

    return True, SUCCESS_MSG


def match_contains(expected, actual):
    expected = expected.strip()
    actual = str(actual)

    if expected in actual:
        return True, SUCCESS_MSG
    else:
        return False, "Expected %s but got %s" % (expected, actual)


def default_matcher(expected, actual):
    if expected == actual:
        return True, SUCCESS_MSG
    else:
        return False, "Expected %s but got %s" % (expected, actual)


def is_almost_equal(expected, actual, threshold):
    abs_threshold = fabs(expected * threshold)
    delta = fabs(expected - actual)
    if delta < abs_threshold:
        return True, SUCCESS_MSG
    else:
        return False, "Expected %s±%s but get %s" % (expected, abs_threshold, actual)


def parse_threshold(expected):
    if "threshold" not in expected:
        return DEFAULT_APPROXIMATE_THRESHOLD, expected

    parts = expected.split("threshold")
    threshold = _parse_single_number(parts[1])
    return threshold, parts[0]


def len_match(expected, actual):
    try:
        len(actual)
    except Exception as e:
        return False, str(e)

    expected = expected.strip()
    threshold, expected = parse_threshold(expected)
    expected_value = _parse_single_number(expected)
    actual_value = len(actual)

    if expected.startswith("~"):
        return is_almost_equal(expected_value, actual_value, threshold)

    return default_matcher(expected_value, actual_value)


def len_greater_match(expected, actual):
    try:
        len(actual)
    except Exception as e:
        return False, str(e)

    expected_value = _parse_single_number(expected.strip())
    actual_value = len(actual)

    return actual_value > expected_value, "Expected %s>%s" % (actual_value, expected_value)


def len_less_match(expected, actual):
    try:
        len(actual)
    except Exception as e:
        return False, str(e)

    expected_value = _parse_single_number(expected.strip())
    actual_value = len(actual)

    return actual_value < expected_value, "Expected %s<%s" % (actual_value, expected_value)


def approximate_match(expected, actual):
    expected = expected.strip()
    threshold, expected = parse_threshold(expected)
    expected_value = _parse_single_number(expected)
    actual = float(actual)
    return is_almost_equal(expected_value, actual, threshold)


def date_matcher(expected, actual):
    expected = expected.strip()

    if expected == "today":
        expected = datetime.today().date()
        actual = datetime.strptime(actual[0:10], "%Y-%m-%d").date()
    else:
        return False, "DATE FORMAT '%s' NOT SUPPORTED!" % expected

    if actual == expected:
        return True, SUCCESS_MSG
    else:
        return False, "Expected %s but got %s" % (expected, actual)


def match_valid_ip(expected, actual):
    if "." in actual:
        return _match_valid_ip4(actual)
    else:
        return _match_valid_ip6(actual)


def _match_valid_ip4(actual):
    parts = actual.split(".")
    if len(parts) != 4:
        return False, "Expected valid ip but got %s" % actual
    for part in parts:
        part = int(part)
        if part < 0 or part > 255:
            return False, "Expected valid ip but got %s" % actual
    return True, ""


def _match_valid_ip6(actual):
    parts = actual.split(":")
    if len(parts) != 7:
        return False, "Expected valid ip but got %s" % actual
    for part in parts:
        if len(part) != 4:
            return False, "Expected valid ip but got %s" % actual
    return True, ""


def file_writer(expected, actual):
    expected = expected.strip()
    file_util.write_tmp(expected, actual)
    return True, SUCCESS_MSG

def file_reader(expected, actual):
    expected = expected.strip()
    data = file_util.read_file_contents(expected)
    data = data.strip()
    is_match = str(data) == str(actual)
    error_msg = "Files content in %s didn't match - expected: %s but got %s" % (expected, data, actual)
    if not is_match:
        log.warning(error_msg)
    return is_match, error_msg

def store_var(expected, actual):
    name, value = expected, actual
    if has(name):
        return False, f"{name} is already declared in this namespace"
    store(name, actual)
    return True, SUCCESS_MSG

def fetch_var(expected, actual):
    name, value = expected, actual
    if not has(name):
        return False, f"{name} is not declared in this namespace"
    val = fetch(name)
    if val != actual:
        return False, f"Expected {val} but got {actual}"
    return True, SUCCESS_MSG

def _parse_single_number(expected):
    # skip characters in the beginning which aren't digits
    index = 0
    for c in expected:
        if c.isdigit() or c == "-":
            break
        index += 1

    return float(expected[index:])


# when brace expansion is not used, just return the same string as passed in
def brace_expand_noop(s):
    return s


# technically not a matcher but this file seems like the best location nonetheless?
# TODO: How to be able to join paths eg urls better, like path.join etc
def brace_expand(s, auto_coerce=False):
    if not isinstance(s, str):
        return s

    s = expand_string(s)

    if auto_coerce:
        return coerce_str_to_int(s)
    else:
        return s

def variable_resolver(variable_name):
    if scope.has(variable_name):
        return scope.fetch(variable_name)
    return None

def file_resolver(variable_name):
    if os.path.isfile(variable_name):
        return file_util.read_file_contents(variable_name)
    return None

resolvers = [variable_resolver, file_resolver]
brace_expansion_regexp = r'<([^<>]+)>'

def expand_string(s):
    pattern = compile_regexp(brace_expansion_regexp)
    try:
        return str_util.expand_string(s, pattern, resolve_funcs=resolvers)
    except ValueError as e:
        log.warning(str(e))
        return s

# def expand_string(s):
#     while match := re.search(r"<(.*?)>", s):
#         if match:
#             substring = match.group(0)
#             var_name = match.group(1)
#
#             # is declared in the scope?
#             if scope.has(var_name):
#                 s = s.replace(substring, scope.fetch(var_name))
#             # maybe it refers to a file?
#             elif os.path.isfile(var_name):
#                 variable_value = file_util.read_file_contents(var_name)
#                 s = s.replace(substring, variable_value)
#             else:
#                 # Ok, time to give up
#                 log.warning(f"Failed to match variable {substring} to anything")
#                 break
#     return s



# # technically not a matcher but this file seems like the best location nonetheless?
# _PLACEHOLDER = re.compile(r"<([A-Za-z0-9_.\-]+)>")
# def brace_expand(s, auto_coerce):
#     # Non-strings pass through
#     if not isinstance(s, str):
#         return s
#
#     # WHOLE-VALUE typed injection: "<NAME>" -> stored value (preserve type)
#     m = _PLACEHOLDER.fullmatch(s)
#     if m:
#         name = m.group(1)
#         if is_in_store(name):
#             return get_from_store(name)
#         if os.path.isfile(name):
#             contents = file_util.read_file_contents(name)
#             return coerce_str_to_int(contents) if auto_coerce else contents
#         log.warning("Failed to resolve <%s> in dir '%s'", name, get_dir_namespace())
#         return s  # leave as-is
#
#     # STRING INTERPOLATION: replace each <NAME> with stringified value
#     def _repl(mm):
#         name = mm.group(1)
#         if is_in_store(name):
#             return str(get_from_store(name))
#         if os.path.isfile(name):
#             return file_util.read_file_contents(name)
#         log.warning("Failed to resolve <%s> in dir '%s'", name, get_dir_namespace())
#         return mm.group(0)  # leave placeholder intact
#
#     out = _PLACEHOLDER.sub(_repl, s)
#     # For interpolation, we keep it a string; optional numeric coercion:
#     return coerce_str_to_int(out) if auto_coerce else out


def add_matcher(matcher_name, matcher_func):
    if matcher_name in matcher_dict:
        raise AssertionError("Duplicate matcher: %s" % matcher_name)
    matcher_dict["$" + matcher_name] = matcher_func


def negating_matcher(negating_name, matcher_func):
    def do_match(expected, actual):
        result, msg = matcher_func(expected, actual)
        if result:
            return False, "Expected negating matcher ('$!%s %s') - to be FALSE but was TRUE for: %s" % (
                negating_name, expected, actual)
        else:
            return True, None

    return do_match


def add_negating_matchers():
    negating_matchers = []
    for matcher_name, matcher_func in matcher_dict.items():
        matcher_name = strip_matcher_prefix(matcher_name)
        negating_matchers.append(("!"+matcher_name, negating_matcher(matcher_name, matcher_func)))

    for name, func in negating_matchers:
        add_matcher(name, func)


matcher_dict = {
    "$valid_url": match_valid_url,
    "$contains": match_contains,
    "$len": len_match,
    "$len_gt": len_greater_match,
    "$len_lt": len_less_match,
    "$~": approximate_match,
    "$date": date_matcher,
    "$write_file": file_writer,
    "$read_file": file_reader,
    "$valid_ip": match_valid_ip,
    "$expects": match_expression,
    "$text": match_text,
    "$regexp": match_regexp,
    "$expr": match_expression,
}
