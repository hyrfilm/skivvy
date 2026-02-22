import pytest

from skivvy import matchers


class DummyResponse:
    def __init__(self, status_code):
        self.status_code = status_code


def test_valid_url_success_uses_tls_verification_by_default(isolated_matcher_state):
    calls = {}

    def fake_get(url, verify):
        calls["url"] = url
        calls["verify"] = verify
        return DummyResponse(200)

    matchers.set_matcher_options({})
    original_get = matchers.requests.get
    matchers.requests.get = fake_get
    try:
        result, msg = matchers.match_valid_url("", "http://example.test/ping")
    finally:
        matchers.requests.get = original_get

    assert (result, msg) == (True, matchers.SUCCESS_MSG)
    assert calls == {"url": "http://example.test/ping", "verify": True}


@pytest.mark.parametrize(
    "expected",
    [
        "prefix http://api.example.test unsafe",
        "unsafe prefix http://api.example.test",
    ],
)
def test_valid_url_parses_prefix_and_unsafe_modifiers_order_independently(
    expected, isolated_matcher_state
):
    calls = {}

    def fake_get(url, verify):
        calls["url"] = url
        calls["verify"] = verify
        return DummyResponse(202)

    original_get = matchers.requests.get
    matchers.requests.get = fake_get
    try:
        result, _ = matchers.match_valid_url(expected, "/health")
    finally:
        matchers.requests.get = original_get

    assert result is True
    assert calls == {"url": "http://api.example.test/health", "verify": False}


def test_valid_url_applies_matcher_options_replace_before_request(isolated_matcher_state):
    calls = {}

    def fake_get(url, verify):
        calls["url"] = url
        calls["verify"] = verify
        return DummyResponse(200)

    matchers.set_matcher_options({"$valid_url": {"replace": {"^//": "http://"}}})
    original_get = matchers.requests.get
    matchers.requests.get = fake_get
    try:
        result, _ = matchers.match_valid_url("", "//example.test/image.png")
    finally:
        matchers.requests.get = original_get

    assert result is True
    assert calls["url"] == "http://example.test/image.png"


def test_valid_url_reports_unexpected_status_code(isolated_matcher_state):
    def fake_get(url, verify):
        return DummyResponse(404)

    original_get = matchers.requests.get
    matchers.requests.get = fake_get
    try:
        result, msg = matchers.match_valid_url("", "http://example.test/missing")
    finally:
        matchers.requests.get = original_get

    assert result is False
    assert "Expected [200, 201, 202] but got 404" in msg


def test_valid_url_ssl_error_includes_unsafe_hint(isolated_matcher_state):
    def fake_get(url, verify):
        raise matchers.requests.exceptions.SSLError("certificate verify failed")

    original_get = matchers.requests.get
    matchers.requests.get = fake_get
    try:
        result, msg = matchers.match_valid_url("", "https://self-signed.example.test")
    finally:
        matchers.requests.get = original_get

    assert result is False
    assert "TLS certificate verification failed" in msg
    assert "add 'unsafe'" in msg


def test_valid_url_generic_request_error_has_no_tls_hint(isolated_matcher_state):
    def fake_get(url, verify):
        raise RuntimeError("connection refused")

    original_get = matchers.requests.get
    matchers.requests.get = fake_get
    try:
        result, msg = matchers.match_valid_url("", "http://example.test/down")
    finally:
        matchers.requests.get = original_get

    assert result is False
    assert "Failed to make request to http://example.test/down" in msg
    assert "add 'unsafe'" not in msg
