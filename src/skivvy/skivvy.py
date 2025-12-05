"""skivvy

Usage:
    skivvy <cfg_file>
    skivvy <cfg_file> [-t]
    skivvy <cfg_file> [-t] -i path.*file...
    skivvy <cfg_file> [-t] -e path.*file...
    skivvy <cfg_file> [-t] -i path.*file... -e path.*file...

    skivvy examples/example.json (run examples)

Options:
    -h --help       show this screen.
    -v --version    show version.
    -i=regexp       include only files matching provided regexp(s) [default: .*]
    -e=regexp       exclude files matching provided regexp(s)
    -t              keep temporary files (if any)
"""

import json
import traceback

from docopt import docopt

from skivvy import __version__
from skivvy.skivvy_config2 import create_testcase, conf_get, Settings, get_all_settings
from . import custom_matchers, test_runner
from . import matchers
from .skivvy_config import read_config
from .util import file_util, http_util, dict_util, str_util
from .util import log
from .util.str_util import tojsonstr
from .verify import verify

version = __version__
STATUS_OK = "OK"
STATUS_FAILED = "FAILED"
log.set_default_level("INFO")


def configure_testcase(test_dict, conf_dict):
    testcase = dict(conf_dict)
    testcase.update(test_dict)
    return testcase


def configure_logging(testcase):
    log_level = testcase.get("log_level", "INFO")
    log.set_default_level(log_level)


def override_default_headers(default_headers, more_headers):
    d = dict(default_headers)
    d.update(more_headers)
    return d


def log_testcase_failed(testfile, conf):
    failure_msg = "\n\n[red]%s\t%s[/red]\n\n" % (testfile, STATUS_FAILED)
    log.error(failure_msg)


def log_error_context(err_context, conf):
    colorize = conf.get("colorize", True)
    e, expected, actual = (
        err_context.get("exception"),
        err_context.get("expected"),
        err_context.get("actual"),
    )
    log.error(str(e))
    if expected:
        log.info("--------------- DIFF BEGIN ---------------")
        diff_output = str_util.pretty_diff(tojsonstr(expected), tojsonstr(actual))
        # diff_output = icdiff2
        # differ = icdiff2.RichConsoleDiff()
        # log.info(differ.print_table(expected, actual))
        log.info(diff_output)
        log.info("--------------- DIFF END -----------------")
        log.debug("************** EXPECTED *****************")
        log.debug("!!! expected:\n%s" % tojsonstr(expected))
        log.debug("**************  ACTUAL *****************")
        log.debug("!!! actual:\n%s" % tojsonstr(actual))
        log.debug("\n" * 5)


def run_test(filename, env_conf):
    file_util.set_current_file(filename)
    error_context = {}

    try:
        testcase = create_testcase(filename, env_conf)
        request, testcase_config = test_runner.create_request(testcase)
        expected_status = testcase_config.get("status")
        expected_response = testcase_config.get("response")
        expected = {}
        if expected_status is not None:
            expected["status"] = expected_status
        if expected_response is not None:
            expected["response"] = expected_response
        error_context["expected"] = expected

        http_envelope = http_util.execute(request)
        actual_status = http_envelope.status_code
        actual_response = http_envelope.json()
        error_context["actual"] = {
            "status": actual_status,
            "response": actual_response,
        }

        if "status" in testcase_config:
            verify(testcase_config["status"], actual_status, **testcase_config)
        if "response" in testcase_config:
            verify(testcase_config["response"], actual_response, **testcase_config)
    except Exception as e:
        error_context["exception"] = traceback.format_exc()
        return STATUS_FAILED, error_context

    return STATUS_OK, None


def handle_upload_file(file):
    if not file:
        return None

    key = list(file.keys())[0]
    filename = open(list(file.values())[0], "rb")
    return {key: filename}


def dump_response_headers(headers_to_write, r):
    for filename in headers_to_write.keys():
        log.debug("writing header: %s" % filename)
        headers = dict_util.subset(r.headers, headers_to_write.get(filename, []))
        file_util.write_tmp(filename, json.dumps(headers))


def run():
    arguments = docopt(__doc__, version=f"skivvy {version}")
    cfg_file = arguments.get("<cfg_file>")
    log.info(f"[b]skivvy[/b] [u]{version}[/u] | config=cfg_file")
    conf = read_config(cfg_file)
    tests = file_util.list_files(conf.tests, conf.ext)
    log.info(f"{len(tests)} tests found.")
    custom_matchers.load(conf)
    matchers.add_negating_matchers()
    fail_fast = conf.get("fail_fast", False)

    failures = 0
    num_tests = 0

    # include files - by inclusive filtering files that match the -i regexps
    # (default is ['.*'] so all files would be included in the filter)
    incl_patterns = arguments.get("-i") or []
    incl_patterns = str_util.compile_regexps(incl_patterns)
    tests = [
        testfile for testfile in tests if str_util.matches_any(testfile, incl_patterns)
    ]

    # exclude files - by removing any files that match the -i regexps (default is [] so no files would be excluded)
    excl_patterns = arguments.get("-e") or []
    excl_patterns = str_util.compile_regexps(excl_patterns)
    tests = [
        testfile
        for testfile in tests
        if not str_util.matches_any(testfile, excl_patterns)
    ]
    log.adjust_col_width(tests)

    for testfile in tests:
        with log.testcase_logger(testfile) as test:
            num_tests += 1
            result, err_context = run_test(testfile, conf)
            if result == STATUS_OK:
                test.ok = True
            else:
                test.ok = False
                log_testcase_failed(testfile, conf)
                log_error_context(err_context, conf)
                failures += 1
                if fail_fast and failures > 0:
                    log.info('[red]Halting test run![/red]("fail_fast" is set to true)')
                    break

    if not arguments.get("-t"):
        log.debug("Removing temporary files...")
        file_util.cleanup_tmp_files()

    return summary(failures, num_tests)


def summary(failures, num_tests):
    if failures > 0:
        log.info("%s testcases of %s failed. :(" % (failures, num_tests))
        return False
    elif num_tests == 0:
        log.info("No tests found!")
        return False
    else:
        log.info("All %s tests passed." % num_tests)
        log.info("Lookin' good!")
        return True


def run_skivvy():
    result = run()
    if not result:
        exit(1)
    else:
        exit(0)


if __name__ == "__main__":
    run_skivvy()
