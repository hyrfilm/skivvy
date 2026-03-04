import pytest

from skivvy.config import (
    create_testcase,
    parse_cli_overrides,
    parse_env_overrides,
    read_config,
)


def test_parse_cli_overrides_coerces_values():
    overrides = parse_cli_overrides(
        [
            "log_level=DEBUG",
            "fail_fast=true",
            "file_order=natural",
            'matcher_options={"$valid_url":{"replace":{"^//":"http://"}}}',
        ]
    )

    assert overrides["log_level"] == "DEBUG"
    assert overrides["fail_fast"] is True
    assert overrides["file_order"] == "natural"
    assert overrides["matcher_options"]["$valid_url"]["replace"]["^//"] == "http://"


def test_parse_cli_overrides_rejects_invalid_format():
    with pytest.raises(ValueError):
        parse_cli_overrides(["log_level"])


def test_parse_cli_overrides_rejects_unknown_setting():
    with pytest.raises(ValueError):
        parse_cli_overrides(["unknown=123"])


def test_parse_cli_overrides_rejects_removed_colorize_setting():
    with pytest.raises(ValueError):
        parse_cli_overrides(["colorize=false"])


def test_parse_cli_overrides_accepts_diff_toggles():
    overrides = parse_cli_overrides(
        [
            "diff_enabled=false",
            "diff_ndiff=false",
            "diff_unified=true",
            "diff_table=true",
            "diff_full=true",
            "diff_compact_lists=false",
        ]
    )

    assert overrides == {
        "diff_enabled": False,
        "diff_ndiff": False,
        "diff_unified": True,
        "diff_table": True,
        "diff_full": True,
        "diff_compact_lists": False,
    }


def test_parse_cli_overrides_accepts_http_log_levels():
    overrides = parse_cli_overrides(
        [
            "http_request_level=INFO",
            "http_response_level=DEBUG",
            "http_headers_level=null",
        ]
    )

    assert overrides == {
        "http_request_level": "INFO",
        "http_response_level": "DEBUG",
        "http_headers_level": None,
    }


def test_parse_env_overrides_reads_known_keys():
    env = {
        "SKIVVY_LOG_LEVEL": "WARNING",
        "SKIVVY_FAIL_FAST": "TRUE",
        "SKIVVY_FILE_ORDER": "natural",
        "SKIVVY_MATCHER_OPTIONS": '{"$contains":{"min_len":2}}',
        "SKIVVY_HTTP_HEADERS_LEVEL": "OFF",
        "SKIVVY_COLORIZE": "false",
        "SKIVVY_NOT_A_SETTING": "ignored",
    }

    overrides = parse_env_overrides(env)

    assert overrides == {
        "log_level": "WARNING",
        "fail_fast": True,
        "file_order": "natural",
        "matcher_options": {"$contains": {"min_len": 2}},
        "http_headers_level": "OFF",
    }


def test_read_config_returns_empty_dict_when_no_config():
    assert read_config(None) == {}
    assert read_config("") == {}


def test_read_config_reads_json_file(tmp_path):
    cfg = tmp_path / "test.json"
    cfg.write_text('{"base_url": "https://example.com", "fail_fast": true}')
    result = read_config(str(cfg))
    assert result == {"base_url": "https://example.com", "fail_fast": True}


def test_merge_precedence_cli_over_test_over_env_over_cfg():
    cfg = {"log_level": "INFO", "brace_expansion": False}
    env = {"log_level": "WARNING", "brace_expansion": True}
    testcase = {"log_level": "ERROR"}
    cli = {"log_level": "DEBUG"}

    merged = create_testcase(cli, testcase, env, cfg)
    assert merged["log_level"] == "DEBUG"
    assert merged["brace_expansion"] is True
