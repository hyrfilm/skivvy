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


def test_text_matcher_passes_for_printable_strings():
    assert matchers.match_text("", "Leanne Graham")[0] is True
    assert matchers.match_text("", "hello, world!")[0] is True
    assert matchers.match_text("", "user@example.com")[0] is True
    assert matchers.match_text("", "South Elvis")[0] is True
    assert matchers.match_text("", "Leopoldo_Corkery")[0] is True
    assert matchers.match_text("", "42")[0] is True


def test_text_matcher_fails_for_non_printable_characters():
    assert matchers.match_text("", "\x00binary")[0] is False
    assert matchers.match_text("", "tab\there")[0] is False
    assert matchers.match_text("", "newline\nhere")[0] is False


def test_text_matcher_fails_for_empty_string():
    assert matchers.match_text("", "")[0] is False


def test_uuid_matcher_accepts_any_valid_uuid():
    assert matchers.match_uuid("", "550e8400-e29b-41d4-a716-446655440000")[0] is True


def test_uuid_matcher_accepts_specific_version():
    assert matchers.match_uuid("4", "550e8400-e29b-41d4-a716-446655440000")[0] is True


def test_uuid_matcher_rejects_wrong_version():
    result, msg = matchers.match_uuid("4", "6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # v1
    assert result is False
    assert "v4" in msg


def test_uuid_matcher_rejects_non_uuid():
    assert matchers.match_uuid("", "not-a-uuid")[0] is False
    assert matchers.match_uuid("", "12345")[0] is False


def test_in_matcher_accepts_value_in_list():
    assert matchers.match_in("active inactive pending", "active")[0] is True
    assert matchers.match_in("active inactive pending", "pending")[0] is True


def test_in_matcher_rejects_value_not_in_list():
    result, msg = matchers.match_in("active inactive pending", "deleted")
    assert result is False
    assert "deleted" in msg


def test_in_matcher_works_with_integers():
    assert matchers.match_in("200 201 204", 200)[0] is True
    assert matchers.match_in("200 201 204", 500)[0] is False
