from datetime import datetime as real_datetime

import pytest

from skivvy import matchers
from skivvy.verify import verify


def test_regexp_invalid_pattern_returns_parse_error_message():
    result, msg = matchers.match_regexp("[", "abc")

    assert result is False
    assert "Invalid regular expression pattern" in msg


def test_store_and_fetch_matchers_round_trip(isolated_scope_namespace):
    verify("$store token", "abc123")
    verify("$fetch token", "abc123")


def test_store_matcher_fails_for_duplicate_name(isolated_scope_namespace):
    verify("$store token", "abc123")

    with pytest.raises(Exception, match="already declared"):
        verify("$store token", "def456")


def test_fetch_matcher_fails_for_undeclared_name(isolated_scope_namespace):
    with pytest.raises(Exception, match="not declared"):
        verify("$fetch missing_token", "abc123")


def test_write_file_and_read_file_matchers_round_trip(tmp_path, monkeypatch, clean_tmp_files):
    monkeypatch.chdir(tmp_path)

    assert matchers.file_writer(" token.txt ", "abc123") == (True, matchers.SUCCESS_MSG)
    result, _msg = matchers.file_reader(" token.txt ", "abc123")
    assert result is True


def test_date_matcher_supports_today_when_date_prefix_matches(monkeypatch):
    class FixedDateTime:
        @staticmethod
        def today():
            return real_datetime(2025, 1, 2, 12, 0, 0)

        @staticmethod
        def strptime(value, fmt):
            return real_datetime.strptime(value, fmt)

    monkeypatch.setattr(matchers, "datetime", FixedDateTime)

    assert matchers.date_matcher("today", "2025-01-02T23:59:59Z") == (
        True,
        matchers.SUCCESS_MSG,
    )


def test_date_matcher_rejects_unsupported_format():
    result, msg = matchers.date_matcher("yesterday", "2025-01-02")

    assert result is False
    assert "DATE FORMAT" in msg


def test_valid_ip_matcher_ipv4_valid_and_invalid():
    assert matchers.match_valid_ip("", "127.0.0.1")[0] is True
    assert matchers.match_valid_ip("", "300.0.0.1")[0] is False
