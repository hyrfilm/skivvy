"""skivvy

Usage:
    skivvy.py run <cfg_file>
    skivvy.py [-t] run <cfg_file>
    skivvy.py run cfg/example.json (run examples)

Options:
  -h --help         Show this screen.
  -v --version      Show version.
  -t                Keep temporary files (if any)
"""

import json
import logging
from functools import partial
from urlparse import urljoin
from docopt import docopt

import matchers
from util.str_util import tojsonstr, diff_strings
from skivvy_config import read_config
from util import file_util, http_util, dict_util
from util import log_util
from verify import verify

STATUS_OK = "OK"
STATUS_FAILED = "FAILED"

_logger = log_util.get_logger(__name__, level=logging.DEBUG)


def configure_testcase(test_dict, conf_dict):
    testcase = dict(conf_dict)
    testcase.update(test_dict)
    return testcase


def configure_logging(testcase):
    log_level = testcase.get("log_level", None)
    if log_level:
        _logger.setLevel(log_level)


def override_default_headers(default_headers, more_headers):
    d = dict(default_headers)
    d.update(more_headers)
    return d

def deprecation_warnings(testcase):
    if "url_brace_expansion" in testcase:
        print("Warning - 'url_brace_expansion' has been deprecated: use 'brace_expansion' instead.")

def run_test(filename, conf):
    testcase = configure_testcase(file_util.parse_json(filename), conf.as_dict())

    configure_logging(testcase)

    # TODO: should be in a config somewhere
    base_url = testcase.get("base_url", "")
    url = testcase.get("url")
    brace_expansion = testcase.get("url_brace_expansion", False) or testcase.get("brace_expansion", False)
    auto_coerce = testcase.get("auto_coerce", True)
    url = urljoin(base_url, url)
    method = testcase.get("method", "get").lower()
    expected_status = testcase.get("status", 200)
    expected_response = testcase.get("response", {})
    data = testcase.get("body", None)
    upload = testcase.get("upload")
    json_encode_body = testcase.get("json_body", True)
    headers = testcase.get("headers", {})
    content_type = testcase.get("content_type", "application/json")
    headers_to_write = testcase.get("write_headers", {})
    headers_to_read = testcase.get("read_headers", {})
    match_subsets = testcase.get("match_subsets", False)
    match_falsiness = testcase.get("match_falsiness", True)

    match_options = {"match_subsets": match_subsets, "match_falsiness": match_falsiness}

    deprecation_warnings(testcase)

    if headers_to_read:
        headers = override_default_headers(headers, json.load(open(headers_to_read, "r")))

    if data:
        headers = override_default_headers(headers, {"Content-Type": content_type})

    if brace_expansion:
        brace_expander = partial(matchers.brace_expand, auto_coerce=auto_coerce)
    else:
        brace_expander = matchers.brace_expand_noop

    # we expand potential braces in the url... (eg example.com/<replace_me>/)
    url = brace_expander(url)
    # ... and each value in the dict
    data = dict_util.map_nested_dicts_py(data, brace_expander)
    # ... and also in the headers
    headers = dict_util.map_nested_dicts_py(headers, brace_expander)

    if json_encode_body:
        data = json.dumps(data)

    file = handle_upload_file(upload)

    r = http_util.do_request(url, method, data, file, headers, _logger)
    status, json_response, headers_response = r.status_code, http_util.as_json(r), r.headers

    if headers_to_write:
        dump_response_headers(headers_to_write, r)

    _logger.debug("!!! expected:\n%s" % tojsonstr(expected_response))
    _logger.debug("!!! actual:\n%s" % tojsonstr(json_response))

    try:
        verify(expected_status, status, **match_options)
        verify(expected_response, json_response, **match_options)
    except Exception as e:
        _logger.info("--------------- DIFF BEGIN ---------------")
        colorize = conf.get("colorize", True)
        diff_output = diff_strings(tojsonstr(expected_response), tojsonstr(json_response), colorize=colorize)
        _logger.info(diff_output)
        _logger.info("--------------- DIFF END -----------------")

        msg = e.message
        status = STATUS_FAILED
        return status, msg

    return "OK", None  # Yay! it passed.... nothing more to say than that


def handle_upload_file(file):
    if not file:
        return None

    key = file.keys()[0]
    filename = open(file.values()[0], 'rb')
    return {key: filename}


def dump_response_headers(headers_to_write, r):
    for filename in headers_to_write.keys():
        _logger.debug("writing header: %s" % filename)
        headers = dict_util.subset(r.headers, headers_to_write.get(filename, []))
        file_util.write_tmp(filename, json.dumps(headers))


def run():
    arguments = docopt(__doc__, version='skivvy 0.233')
    conf = read_config(arguments.get("<cfg_file>"))
    tests = file_util.list_files(conf.tests, conf.ext)
    failures = 0
    num_tests = 0

    result_format = "%s\t%s"

    for testfile in tests:
        result, msg = run_test(testfile, conf)
        if result == STATUS_FAILED:
            _logger.error(result_format % (testfile, STATUS_FAILED))
            _logger.error(msg)
            failures += 1
        else:
            _logger.info(result_format % (testfile, STATUS_OK))
        num_tests += 1

    if not arguments.get("-t"):
        _logger.debug("Removing temporary files...")
        file_util.cleanup_tmp_files()

    return summary(failures, num_tests)


def summary(failures, num_tests):
    if failures > 0:
        _logger.info("%s testcases of %s failed. :(" % (failures, num_tests))
        return False
    else:
        _logger.info("All %s tests passed." % num_tests)
        _logger.info("Lookin' good!")
        return True


def run_skivvy():
    result = run()
    if not result:
        exit(1)
    else:
        exit(0)


if __name__ == "__main__":
    run_skivvy()
