import pytest

from skivvy.util.http_util2 import initialize_session, do_request


class DummySession:
    """
    Poor man's requests-like session that echoes back the request details.
    """
    def get(self, url, params=None, headers=None):
        return {
            "url": url,
            "method": "get",
            "json": None,
            "data": None,
            "headers": headers,
            "params": params,
        }

    def post(self, url, data=None, json=None, params=None, headers=None):
        return {
            "url": url,
            "method": "post",
            "json": json,
            "data": data,
            "headers": headers,
            "params": params,
        }


def test_get_echoes_inputs():
    initialize_session(DummySession())

    payload = {
        "url": "https://example.com/search",
        "params": {"q": "skivvy", "page": 2},
        "headers": {"Accept": "application/json"},
    }

    result = do_request("get", payload)

    assert result == {
        "url": "https://example.com/search",
        "method": "get",
        "json": None,
        "data": None,
        "headers": {"Accept": "application/json"},
        "params": {"q": "skivvy", "page": 2},
    }


def test_post_with_json_echoes_inputs():
    initialize_session(DummySession())

    payload = {
        "url": "https://example.com/posts",
        "json": {"title": "Hello", "body": "World"},
        "headers": {"Content-Type": "application/json"},
    }

    result = do_request("post", payload)

    assert result == {
        "url": "https://example.com/posts",
        "method": "post",
        "json": {"title": "Hello", "body": "World"},
        "data": None,
        "headers": {"Content-Type": "application/json"},
        "params": None,
    }


def test_post_with_form_and_params_echoes_inputs():
    initialize_session(DummySession())

    payload = {
        "url": "https://example.com/login",
        "data": {"user": "u", "pass": "p"},
        "params": {"redirect": "/home"},
    }

    result = do_request("post", payload)

    assert result == {
        "url": "https://example.com/login",
        "method": "post",
        "json": None,
        "data": {"user": "u", "pass": "p"},
        "headers": None,
        "params": {"redirect": "/home"},
    }
