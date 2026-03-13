"""skivvy

Usage:
    skivvy <target> [-t] [-i=regexp]... [-e=regexp]... [--set=kv]...
    skivvy --help
    skivvy --help-settings
    skivvy --help-matchers

Options:
    -h --help           show this screen.
    --help-settings     list all available settings with defaults and descriptions
    --help-matchers     list all available matchers with descriptions
    -v --version        show version.
    <target>            path to a config JSON file or a test directory
    -i=regexp           include only files matching provided regexp(s)
    -e=regexp           exclude files matching provided regexp(s)
    --set=kv            override a setting using key=value syntax (repeatable);
                        environment overrides use SKIVVY_<SETTING>
    -t                  keep temporary files (if any)

Examples:
    skivvy examples/dev_server/cfg.json
    skivvy examples/dev_server/tests

    specify either a single config file, or a directory of tests
"""

import json
import os
import traceback

from docopt import docopt

from skivvy import __version__
from skivvy.config import (
    Settings,
    conf_get,
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


def configure_logging(testcase):
    log_level = testcase.get("log_level", "INFO")
    log.set_default_level(log_level)


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
        http_envelope = http_util.execute(request, timeout=conf_get(testcase_config, Settings.TIMEOUT))
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


def dump_response_headers(headers_to_write, r):
    for filename in headers_to_write.keys():
        log.debug("writing header: %s" % filename)
        headers = dict_util.subset(r.headers, headers_to_write.get(filename, []))
        file_util.write_tmp(filename, json.dumps(headers))


def normalize_headers(headers: dict) -> dict:
    return {k.lower(): v for k, v in headers.items()}


def _format_option_default(option) -> str:
    return "" if option.default is None or option.default == "" else str(option.default)


def print_settings_help():
    from rich.table import Table
    from .config import get_all_settings

    table = Table(show_header=True, header_style="bold")
    table.add_column("Setting")
    table.add_column("Default")
    table.add_column("Description")
    for option in get_all_settings():
        table.add_row(option.key, _format_option_default(option), option.help)
    log.render(table)


def settings_markdown() -> str:
    from .config import get_all_settings

    lines = ["| Setting | Default | Description |", "| --- | --- | --- |"]
    for option in get_all_settings():
        lines.append(f"| `{option.key}` | `{_format_option_default(option)}` | {option.help} |")
    return "\n".join(lines)


def print_matchers_help():
    from rich.table import Table

    table = Table(show_header=True, header_style="bold")
    table.add_column("Matcher")
    table.add_column("Description")
    for name, func in matchers.matcher_dict.items():
        table.add_row(name, (func.__doc__ or "").strip())
    log.render(table)


def matchers_markdown() -> str:
    lines = ["| Matcher | Description |", "| --- | --- |"]
    for name, func in matchers.matcher_dict.items():
        lines.append(f"| `{name}` | {(func.__doc__ or '').strip()} |")
    return "\n".join(lines)


def run():
    run_id = events.new_run_id()
    events.reset_runtime_listener()
    arguments = None
    target = None
    failures = 0
    num_tests = 0
    result = None
    sink_installation = None

    try:
        arguments = docopt(__doc__, version=f"skivvy {version}")
        if arguments.get("--help-settings"):
            print_settings_help()
            return True
        if arguments.get("--help-matchers"):
            print_matchers_help()
            return True
        target = arguments.get("<target>")
        if target and os.path.isdir(target):
            cfg_conf = {"tests": os.path.abspath(target)}
        else:
            cfg_conf = read_config(target)
        env_overrides = parse_env_overrides()
        cli_overrides = parse_cli_overrides(arguments.get("--set"))

        base_conf = create_testcase(env_overrides, cfg_conf)
        suite_conf = create_testcase(cli_overrides, base_conf)

        # TODO: Temporary experimental flags (_timing/_http_timing) are read here
        # until we finalize the real logging/timing/diffs config design.
        sink_installation = sinks.install_runtime_sinks(suite_conf)

        tests = file_util.list_files(
            suite_conf["tests"],
            conf_get(suite_conf, Settings.EXT),
            file_order=conf_get(suite_conf, Settings.FILE_ORDER),
        )
        custom_matchers.load(suite_conf)
        matchers.add_negating_matchers()
        fail_fast = conf_get(suite_conf, Settings.FAIL_FAST)

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
            config_file=target,
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
                config_file=target,
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
