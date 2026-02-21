import logging
import os
import pprint
import pytest
from skivvy.skivvy import run_test, STATUS_OK, STATUS_FAILED
from skivvy.skivvy_config2 import Option, Settings, create_test_config
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
