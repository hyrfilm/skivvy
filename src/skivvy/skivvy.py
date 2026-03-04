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
import traceback

from docopt import docopt

from skivvy import __version__
from skivvy.config import (
    create_testcase,
    parse_env_overrides,
    parse_cli_overrides,
    read_config,
)
from . import custom_matchers, test_runner
from . import matchers
from . import events
from . import sinks
from .errors import ExpectedTestFailure
from .util import file_util, http_util, dict_util, str_util
from .util import log
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


def run_test(filename, env_conf, cli_overrides=None):
    file_util.set_current_file(filename)
    error_context = {}
    current_step = None

    try:
        current_step = events.CREATE_TESTCASE
        events.emit(current_step)
        testcase = create_testcase(cli_overrides or {}, filename, env_conf)
        current_step = None

        configure_logging(testcase)

        current_step = events.CREATE_REQUEST
        events.emit(current_step)
        request, testcase_config = test_runner.create_request(testcase)
        current_step = None

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

        current_step = events.EXECUTE_REQUEST
        events.emit(current_step)
        http_envelope = http_util.execute(request)
        current_step = None

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
            current_step = events.VERIFY_STATUS
            events.emit(current_step)
            verify(testcase_config["status"], actual_status, **testcase_config)
            current_step = None

        if "response" in testcase_config:
            current_step = events.VERIFY_RESPONSE
            events.emit(current_step)
            verify(testcase_config["response"], actual_response, **testcase_config)
            current_step = None

        if expected_response_headers is not None:
            current_step = events.VERIFY_RESPONSE_HEADERS
            events.emit(current_step)
            verify(
                normalize_headers(expected_response_headers),
                actual_headers,
                **testcase_config,
            )
            current_step = None
    except Exception as e:
        if current_step is not None:
            error_context["failed_step"] = current_step
        error_context["exception"] = str(e)
        if isinstance(e, ExpectedTestFailure):
            error_context["expected_failure"] = True
            if log.is_debug_enabled():
                error_context["traceback"] = traceback.format_exc()
        else:
            error_context["traceback"] = traceback.format_exc()
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
    run_id = events.new_run_id()
    events.reset_runtime_listener()
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
        cfg_conf = read_config(cfg_file)
        env_overrides = parse_env_overrides()
        cli_overrides = parse_cli_overrides(arguments.get("--set"))

        base_conf = create_testcase(env_overrides, cfg_conf)
        suite_conf = create_testcase(cli_overrides, base_conf)

        # TODO: Temporary experimental flags (_timing/_http_timing) are read here
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
        events.emit(
            events.RUN_STARTED,
            run_id=run_id,
            version=version,
            config_file=cfg_file,
            test_count=len(tests),
        )

        for index, testfile in enumerate(tests, start=1):
            num_tests += 1
            events.emit(
                events.TEST_STARTED,
                index=index,
                testfile=testfile,
                test_id=testfile,
            )
            test_result, err_context = run_test(
                testfile,
                suite_conf,
                cli_overrides=cli_overrides,
            )
            if test_result == STATUS_OK:
                events.emit(events.TEST_PASSED)
            else:
                events.emit(
                    events.TEST_FAILED,
                    error_context=err_context,
                    exception=(err_context or {}).get("exception"),
                    expected=(err_context or {}).get("expected"),
                    actual=(err_context or {}).get("actual"),
                )
                failures += 1
                if fail_fast and failures > 0:
                    events.emit(
                        events.TEST_FINISHED,
                        success=False,
                    )
                    break
            events.emit(
                events.TEST_FINISHED,
                success=(test_result == STATUS_OK),
            )

        if not arguments.get("-t"):
            log.debug("Removing temporary files...")
            file_util.cleanup_tmp_files()

        result = summarize_result(failures, num_tests)
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
            )
        finally:
            if sink_installation is not None:
                sink_installation.close()


def summarize_result(failures, num_tests):
    return failures == 0 and num_tests > 0


def run_skivvy():
    result = run()
    if not result:
        exit(1)
    else:
        exit(0)


if __name__ == "__main__":
    run_skivvy()
