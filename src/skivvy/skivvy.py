"""skivvy

Usage:
    skivvy <cfg_file> [-t] [-i=regexp]... [-e=regexp]... [--set=kv]...

    skivvy examples/example.json (run examples)

Options:
    -h --help       show this screen.
    -v --version    show version.
    -i=regexp       include only files matching provided regexp(s)
    -e=regexp       exclude files matching provided regexp(s)
    --set=kv        override a setting using key=value syntax (repeatable)
    -t              keep temporary files (if any)
"""

import json
import time
import traceback

from docopt import docopt

from skivvy import __version__
from skivvy.skivvy_config2 import (
    create_testcase,
    parse_env_overrides,
    parse_cli_overrides,
)
from . import custom_matchers, test_runner
from . import matchers
from . import events
from . import sinks
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
        # TODO: Should we support both of these diffs or only one?
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
        # TODO: Replace legacy direct diff logging with sink-driven configurable rendering
        # after the final logging/timing/diffs config design is chosen.


def run_test(filename, env_conf, cli_overrides=None):
    file_util.set_current_file(filename)
    error_context = {}

    try:
        with events.phase_span("create_testcase", testfile=filename):
            testcase = create_testcase(cli_overrides or {}, filename, env_conf)
        configure_logging(testcase)
        with events.phase_span("create_request", testfile=filename):
            request, testcase_config = test_runner.create_request(testcase)
        expected_status = testcase_config.get("status")
        expected_response = testcase_config.get("response")
        expected = {}
        if expected_status is not None:
            expected["status"] = expected_status
        if expected_response is not None:
            expected["response"] = expected_response
        expected_response_headers = testcase_config.get("response_headers")
        if expected_response_headers is not None:
            expected["response_headers"] = expected_response_headers
        error_context["expected"] = expected

        with events.phase_span("http_execute", testfile=filename):
            http_envelope = http_util.execute(request)
        actual_status = http_envelope.status_code
        actual_response = http_envelope.json()
        actual_headers = normalize_headers(http_envelope.headers)

        headers_to_write = testcase_config.get("write_headers")
        if headers_to_write:
            dump_response_headers(headers_to_write, http_envelope)

        error_context["actual"] = {
            "status": actual_status,
            "response": actual_response,
            "response_headers": actual_headers,
        }

        if "status" in testcase_config:
            with events.phase_span("verify_status", testfile=filename):
                verify(testcase_config["status"], actual_status, **testcase_config)
        if "response" in testcase_config:
            with events.phase_span("verify_response", testfile=filename):
                verify(testcase_config["response"], actual_response, **testcase_config)
        if expected_response_headers is not None:
            with events.phase_span("verify_response_headers", testfile=filename):
                verify(
                    normalize_headers(expected_response_headers),
                    actual_headers,
                    **testcase_config,
                )
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


def normalize_headers(headers: dict) -> dict:
    return {k.lower(): v for k, v in headers.items()}


def run():
    run_started = time.perf_counter()
    run_id = events.new_run_id()
    arguments = None
    cfg_file = None
    failures = 0
    num_tests = 0
    result = None
    sink_installation = None

    try:
        arguments = docopt(__doc__, version=f"skivvy {version}")
        # TODO: Since we started supporting env variables & --set we don't strictly require a cfg file anymore and it makes sense to not require it
        cfg_file = arguments.get("<cfg_file>")
        log.info(f"[b]skivvy[/b] [u]{version}[/u] | config={cfg_file}")
        cfg_conf = read_config(cfg_file)
        env_overrides = parse_env_overrides()
        cli_overrides = parse_cli_overrides(arguments.get("--set"))

        base_conf = create_testcase(env_overrides, cfg_conf)
        suite_conf = create_testcase(cli_overrides, base_conf)

        # TODO: Temporary experimental flags (_rich/_timing/_http_timing) are read here
        # until we finalize the real logging/timing/diffs config design.
        sink_installation = sinks.install_runtime_sinks(suite_conf)

        # TODO: Place these in Settings
        tests = file_util.list_files(
            # TODO: should be required
            suite_conf["tests"],
            # TODO: should not be required (should default to ".json")
            suite_conf["ext"],
            file_order=suite_conf["file_order"],
        )
        log.info(f"{len(tests)} tests found.")
        custom_matchers.load(suite_conf)
        matchers.add_negating_matchers()
        # TODO: Use Settings.FAIL_FAST instead of hard-coded string
        fail_fast = suite_conf.get("fail_fast", False)

        # TODO: The handling of -i/-e is a bit gnarly and not DRY, at least move the relevant parts out into one of the utils
        # include files - by inclusive filtering files that match the -i regexps
        # (default is ['.*'] so all files would be included in the filter)
        incl_patterns = arguments.get("-i") or []
        if isinstance(incl_patterns, str):
            incl_patterns = [incl_patterns]
        if len(incl_patterns) == 0:
            incl_patterns = [".*"]
        incl_patterns = str_util.compile_regexps(incl_patterns)
        tests = [
            testfile for testfile in tests if str_util.matches_any(testfile, incl_patterns)
        ]

        # exclude files - by removing any files that match the -i regexps (default is [] so no files would be excluded)
        excl_patterns = arguments.get("-e") or []
        if isinstance(excl_patterns, str):
            excl_patterns = [excl_patterns]
        excl_patterns = str_util.compile_regexps(excl_patterns)
        tests = [
            testfile
            for testfile in tests
            if not str_util.matches_any(testfile, excl_patterns)
        ]
        log.adjust_col_width(tests)
        events.emit(
            events.RUN_STARTED,
            run_id=run_id,
            config_file=cfg_file,
            test_count=len(tests),
        )

        for index, testfile in enumerate(tests, start=1):
            test_started = time.perf_counter()
            with log.testcase_logger(testfile) as test:
                num_tests += 1
                with events.with_context(run_id=run_id, test_id=testfile, testfile=testfile):
                    events.emit(
                        events.TEST_STARTED,
                        index=index,
                        testfile=testfile,
                    )
                    test_result, err_context = run_test(
                        testfile,
                        suite_conf,
                        cli_overrides=cli_overrides,
                    )
                    elapsed_ms = (time.perf_counter() - test_started) * 1000
                    if test_result == STATUS_OK:
                        test.ok = True
                        events.emit(
                            events.TEST_PASSED,
                            testfile=testfile,
                            elapsed_ms=elapsed_ms,
                        )
                    else:
                        test.ok = False
                        events.emit(
                            events.TEST_FAILED,
                            testfile=testfile,
                            elapsed_ms=elapsed_ms,
                            error_context=err_context,
                            exception=(err_context or {}).get("exception"),
                            expected=(err_context or {}).get("expected"),
                            actual=(err_context or {}).get("actual"),
                        )
                        log_testcase_failed(testfile, suite_conf)
                        log_error_context(err_context, suite_conf)
                        failures += 1
                        if fail_fast and failures > 0:
                            log.info('[red]Halting test run![/red]("fail_fast" is set to true)')
                            events.emit(
                                events.TEST_FINISHED,
                                testfile=testfile,
                                elapsed_ms=elapsed_ms,
                                success=False,
                            )
                            break
                    events.emit(
                        events.TEST_FINISHED,
                        testfile=testfile,
                        elapsed_ms=elapsed_ms,
                        success=(test_result == STATUS_OK),
                    )

        if not arguments.get("-t"):
            log.debug("Removing temporary files...")
            file_util.cleanup_tmp_files()

        result = summary(failures, num_tests)
        events.emit(
            events.RUN_PASSED if result else events.RUN_FAILED,
            run_id=run_id,
            num_tests=num_tests,
            failures=failures,
            success=result,
        )
        return result
    finally:
        try:
            # TODO: Expand run.finished semantics for unexpected top-level exceptions if needed.
            events.emit(
                events.RUN_FINISHED,
                run_id=run_id,
                config_file=cfg_file,
                num_tests=num_tests,
                failures=failures,
                success=result,
                elapsed_ms=(time.perf_counter() - run_started) * 1000,
            )
        finally:
            if sink_installation is not None:
                sink_installation.close()


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
