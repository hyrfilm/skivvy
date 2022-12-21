# coding=utf-8
import string
from datetime import datetime
from math import fabs
import re
import os.path

from util.str_util import coerce_str_to_int
from util import file_util

import requests

from util import log_util

_logger = log_util.get_logger(__name__)

DEFAULT_APPROXIMATE_THRESHOLD = 0.05  # default margin of error for a ~value to still be considered equal to another
SUCCESS_MSG = "OK"


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
        return False, u"Expected '%s' to evaluate to True but was evaluated to False" % actual


def match_regexp(expected, actual):
    try:
        expected = expected.strip()
        _logger.debug("Comparing '%s' to regexp: '%s'" % (actual, expected))
        if re.match(expected, actual):
            _logger.debug("It's a match.")
            return True, SUCCESS_MSG
        else:
            return False, u"Expected '%s' to match regular expression '%s' - but didn't" % (actual, expected)
    except:
        return False, u"Invalid regular expression in testcase: %s" % expected


def match_valid_url(expected, actual):
    try:
        # we allow relative urls using the format "$valid_url /some_url prefix example.com" -> example.com/some_url
        relative_url = expected.split("prefix")
        if len(relative_url) == 2:
            prefix = relative_url[-1]
            prefix = prefix.strip()
            actual = prefix + actual

        valid_status_codes = [200]
        _logger.debug("Making request to %s" % actual)
        response = requests.get(actual, verify=False)
        if response.status_code in valid_status_codes:
            _logger.debug("Success.")
            return True, SUCCESS_MSG
        else:
            _logger.debug("Failure.")
            return False, u"Expected %s but got %s" % (valid_status_codes, actual)
    except Exception as e:
        _logger.error("ERROR - http call failed for: %s" % actual)
        _logger.error("ERROR - expected: %s" % expected)
        raise e


def match_text(expected, actual):
    if not actual:
        return False, u"Expected %s but got %s" % (expected, actual)

    for c in actual:
        if c not in string.ascii_letters:
            return False, u"Expected %s but got %s" % (expected, actual)

    return True, SUCCESS_MSG


def match_contains(expected, actual):
    expected = expected.strip()
    actual = str(actual)

    if expected in actual:
        return True, SUCCESS_MSG
    else:
        return False, u"Expected %s but got %s" % (expected, actual)


def default_matcher(expected, actual):
    if expected == actual:
        return True, SUCCESS_MSG
    else:
        return False, u"Expected %s but got %s" % (expected, actual)


def is_almost_equal(expected, actual, threshold):
    abs_threshold = fabs(expected * threshold)
    delta = fabs(expected - actual)
    if delta < abs_threshold:
        return True, SUCCESS_MSG
    else:
        return False, u"Expected %s±%s but get %s" % (expected, abs_threshold, actual)


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

    return actual_value > expected_value, u"Expected %s>%s" % (actual_value, expected_value)


def len_less_match(expected, actual):
    try:
        len(actual)
    except Exception as e:
        return False, str(e)

    expected_value = _parse_single_number(expected.strip())
    actual_value = len(actual)

    return actual_value < expected_value, u"Expected %s<%s" % (actual_value, expected_value)


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
        _logger.warn(error_msg)
    return is_match, error_msg


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
def brace_expand(s, auto_coerce):
    if not isinstance(s, basestring):
        return s

    while True:
        match = re.search(r"\<.*?\>", s)
        if not match:
            break
        else:
            variable = match.group(0)
            variable_name = variable.replace("<", "").replace(">", "")
            # maybe it refers to a file?
            if not os.path.isfile(variable_name):
                # Oh well, I give up! ;)
                _logger.warn("Failed to match variable %s to anything" % variable)
                break
            else:
                variable_value = file_util.read_file_contents(variable_name)
                s = s.replace(variable, variable_value)

    if auto_coerce:
        return coerce_str_to_int(s)
    else:
        return s


def add_matcher(matcher_name, matcher_func):
    if matcher_name in matcher_dict:
        raise AssertionError("Duplicate matcher: %s" % matcher_name)
    matcher_dict["$" + matcher_name] = matcher_func


def negating_matcher(negating_name, matcher_func):
    def do_match(expected, actual):
        result, msg = matcher_func(expected, actual)
        if result:
            return False, u"Expected negating matcher ('$!%s %s') - to be FALSE but was TRUE for: %s" % (
                negating_name, expected, actual)
        else:
            return True, None

    return do_match


def add_negating_matchers():
    for matcher_name, matcher_func in matcher_dict.items():
        matcher_name = strip_matcher_prefix(matcher_name)
        add_matcher("!"+matcher_name, negating_matcher(matcher_name, matcher_func))


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
