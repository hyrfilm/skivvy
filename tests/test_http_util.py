import pytest

from skivvy.util.http_util2 import initialize_session, do_request, prepare_request_data


class DummySession:
    """
    Poor man's requests-like session that echoes back the request details.
    """
    def get(self, **kwargs):
        return {
            "url": kwargs.get("url"),
            "method": "get",
            "json": None,
            "data": None,
            "headers": kwargs.get("headers"),
            "params": kwargs.get("params"),
        }

    def post(self, **kwargs):
        return {
            "url": kwargs.get("url"),
            "method": "post",
            "json": kwargs.get("json"),
            "data": kwargs.get("data"),
            "headers": kwargs.get("headers"),
            "params": kwargs.get("params"),
        }


@pytest.fixture
def dummy_session():
    # setup
    session = initialize_session(DummySession())
    yield session
    # teardown
    initialize_session(None)

def test_get_echoes_inputs(dummy_session):
    payload = {
        "url": "https://example.com/search",
        "params": {"q": "skivvy", "page": 2},
        "headers": {"Accept": "application/json"},
    }

    result = do_request("get", **payload)

    assert result == {
        "url": "https://example.com/search",
        "method": "get",
        "json": None,
        "data": None,
        "headers": {"Accept": "application/json"},
        "params": {"q": "skivvy", "page": 2},
    }


def test_post_with_json_echoes_inputs(dummy_session):
    payload = {
        "url": "https://example.com/posts",
        "json": {"title": "Hello", "body": "World"},
        "headers": {"Content-Type": "application/json"},
    }

    result = do_request("post", **payload)

    assert result == {
        "url": "https://example.com/posts",
        "method": "post",
        "json": {"title": "Hello", "body": "World"},
        "data": None,
        "headers": {"Content-Type": "application/json"},
        "params": None,
    }

def test_post_with_form_and_params_echoes_inputs(dummy_session):
    payload = {
        "url": "https://example.com/login",
        "data": {"user": "u", "pass": "p"},
        "params": {"redirect": "/home"},
    }

    result = do_request("post", **payload)

    assert result == {
        "url": "https://example.com/login",
        "method": "post",
        "json": None,
        "data": {"user": "u", "pass": "p"},
        "headers": None,
        "params": {"redirect": "/home"},
    }

def test_mapping_skivvy_fields_to_requests_api():
    # these are the names of the fields skivvy uses:
    method, requests_api_fields = prepare_request_data(
        {"method": "POST",
         "url": "example.com",
         "query": {"page": 123},
         "upload": "some-binary-data",
         "body": {"some": "hip JSON data"},
         "form": {"olden": "quaint internet days"}
         })

    # re-mapped to what requests expects:
    expected_data = {'data': {'olden': 'quaint internet days'},
                     'files': 'some-binary-data',
                     'json': {'some': 'hip JSON data'},
                     'params': {'page': 123},
                     'url': 'example.com'}
    assert method == "post"
    assert requests_api_fields == expected_data
