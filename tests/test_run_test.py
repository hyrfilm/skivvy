import logging
import os
import pprint
import json
import pytest
import sys
from skivvy.skivvy import run_test, run, STATUS_OK, STATUS_FAILED
from skivvy.skivvy_config2 import Option, Settings, create_test_config
from skivvy.test_runner import create_request
from skivvy.util import file_util, log, str_util

FAKE_SERVER = "localhost"
FAKE_PORT = 8888


@pytest.fixture
def my_httpserver(request, httpserver):
    request.cls.httpserver = httpserver


default_cfg = {"base_url": f"http://{FAKE_SERVER}:{FAKE_PORT}", "log_level": "DEBUG"}


@pytest.fixture(scope="session")
def httpserver_listen_address():
    return (FAKE_SERVER, FAKE_PORT)


def test_fortune_01_successful(httpserver):
    httpserver.expect_request("/api/fortune/1").respond_with_json(
        {"wisdom": "If it seems that fates are aginst you today, they probably are."}
    )
    status, error_context = run_test(
        "./tests/fixtures/testcases/check_status.json", default_cfg
    )
    assert status is STATUS_OK
    assert error_context is None


def test_fortune_01_failing(httpserver):
    # lowercase i should make it fail since it's doing an exact match
    httpserver.expect_request("/api/fortune/1").respond_with_json(
        {"wisdom": "If it seems that fates are aginst you today, they probably are."}
    )
    status, error_context = run_test(
        "./tests/fixtures/testcases/check_exact_match.json", default_cfg
    )
    assert status is STATUS_FAILED
    assert "if it seems" in error_context.get("expected").get("response").get("wisdom")
    assert "If it seems" in error_context.get("actual").get("response").get("wisdom")


def test_fortune_02_match_subsets(httpserver):
    httpserver.expect_request("/api/fortune").respond_with_json(
        {"wisdom": "You only live once."}
    )
    status, error_context = run_test(
        "./tests/fixtures/testcases/match_subset.json", default_cfg
    )
    assert status is STATUS_OK
    # assert error_context is None


def test_match_subsets_missing_key_fails_by_default(httpserver):
    # Some entries lack the 'score' key entirely; with match_subsets, this should
    # fail by default unless skip_empty_objects is enabled AND they are empty objects.
    httpserver.expect_request("/api/items").respond_with_json(
        {"items": [{"name": "Alice", "score": 42}, {"name": "Bob"}]}
    )
    status, error_context = run_test(
        "./tests/fixtures/testcases/match_subset_missing_key.json", default_cfg
    )
    assert status is STATUS_FAILED
    assert error_context is not None


def test_match_subsets_empty_object_can_be_skipped(httpserver):
    httpserver.expect_request("/api/items").respond_with_json(
        {"items": [{"score": 42}, {}]}
    )
    status, error_context = run_test(
        "./tests/fixtures/testcases/match_subset_empty_object_skip.json",
        default_cfg,
    )
    assert status is STATUS_OK
    assert error_context is None


def test_brace_expansion_warnings_non_strict_returns_unexpanded_url():
    testcase = create_test_config({
        "base_url": f"http://{FAKE_SERVER}:{FAKE_PORT}",
        "url": "<undefined_brace_expansion_var>/api/data",
        "method": "get",
        "brace_expansion": True,
        "brace_expansion_warnings": True,
        "brace_expansion_strict": False,
    })
    request, _ = create_request(testcase)
    assert "<undefined_brace_expansion_var>" in request["url"]


def test_brace_expansion_strict_raises_on_undefined_variable():
    testcase = create_test_config({
        "base_url": f"http://{FAKE_SERVER}:{FAKE_PORT}",
        "url": "<undefined_brace_expansion_var>/api/data",
        "method": "get",
        "brace_expansion": True,
        "brace_expansion_warnings": False,
        "brace_expansion_strict": True,
    })
    with pytest.raises(ValueError):
        create_request(testcase)


def test_run_test_supports_brace_expansion_from_environment(httpserver, tmp_path, monkeypatch):
    monkeypatch.setenv("USER_ID", "123")
    httpserver.expect_request("/api/123").respond_with_json({"ok": True})

    testcase = {
        "url": "/api/<env.USER_ID>",
        "method": "get",
        "status": 200,
        "brace_expansion": True,
    }
    testcase_file = tmp_path / "env_brace_expansion.json"
    testcase_file.write_text(json.dumps(testcase))

    status, error_context = run_test(str(testcase_file), default_cfg)
    assert status is STATUS_OK
    assert error_context is None


def test_matcher_options_valid_url_protocol_relative(httpserver):
    # API returns a protocol-relative URL; matcher_options expands it to http:// before validating
    httpserver.expect_request("/api/photo").respond_with_json(
        {"url": f"//{FAKE_SERVER}:{FAKE_PORT}/image.png"}
    )
    httpserver.expect_request("/image.png").respond_with_data(b"", status=200)
    status, error_context = run_test(
        "./tests/fixtures/testcases/matcher_options_valid_url.json",
        {
            **default_cfg,
            "matcher_options": {
                "$valid_url": {"replace": {"^//": "http://"}}
            },
        },
    )
    assert status is STATUS_OK
    assert error_context is None


def test_cli_overrides_take_precedence_over_test_file(httpserver, tmp_path):
    httpserver.expect_request("/api/fortune/1").respond_with_json(
        {"wisdom": "If it seems that fates are aginst you today, they probably are."}
    )

    testcase = {
        "url": "/api/fortune/1",
        "method": "get",
        "status": 200,
        "log_level": "DEBUG",
    }
    testcase_file = tmp_path / "test.json"
    testcase_file.write_text(json.dumps(testcase))

    logger = logging.getLogger("skivvy.util.log")
    original_level = logger.level
    try:
        status, error_context = run_test(
            str(testcase_file),
            default_cfg,
            cli_overrides={"log_level": "ERROR"},
        )
        assert status is STATUS_OK
        assert error_context is None
        assert logger.level == logging.ERROR
    finally:
        logger.setLevel(original_level)


def test_run_without_include_filters_does_not_crash(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "01.json").write_text(
        json.dumps({"url": "/api/fortune/1", "status": 200, "response": {}})
    )

    cfg = {
        "tests": str(tests_dir),
        "ext": ".json",
        "base_url": "http://127.0.0.1:1",
        "log_level": "ERROR",
        "fail_fast": True,
    }
    cfg_file = tmp_path / "cfg.json"
    cfg_file.write_text(json.dumps(cfg))

    old_argv = sys.argv
    try:
        sys.argv = ["skivvy", str(cfg_file), "-t"]
        result = run()
    finally:
        sys.argv = old_argv

    assert result is False
