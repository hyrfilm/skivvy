from skivvy.test_runner import create_request
from skivvy.util.scope import store

def test_create_request_with_brace_expansion():
    # Set up some variables in our current scope
    store("user_id", "12345")
    store("api_key", "s3cr3t")

    # we want the finished request that:
    # 1. has been joined with the base url
    # 2. has the correct user id
    # 3. has the correct api token
    test_config = {
        "base_url": "https://api.example.com",
        "url": "/users/<user_id>",
        "method": "GET",
        "brace_expansion": True,
        "auto_coerce": True,
        "write_headers": {"Authorization": "Bearer <api_key>"}
    }

    request_dict, complete_dict = create_request(test_config)

    assert request_dict == {
        "method": "GET",
        "url": "https://api.example.com/users/12345",
    }

    assert complete_dict["url"] == "https://api.example.com/users/12345"
    assert complete_dict["write_headers"]["Authorization"] == "Bearer s3cr3t"

def test_brace_expansion_with_files_and_variables():
    # Set up some variables in our current scope
    store("number", "23")

    # same thing as above, but now we are using the (mostly legacy) way
    # of retrieving variables from a file in our fixture dir
    test_config = {
        "base_url": "https://api.example.com",
        "url": "<tests/fixtures/user_id.txt>/hail-satan",
        "body": {"lucky": "<number>" },
        "method": "POST",
        "brace_expansion": True,
        "auto_coercion": True
    }

    request_dict, complete_dict = create_request(test_config)

    assert request_dict == {
        "method": "POST",
        "url": "https://api.example.com/666/hail-satan",
        "body": {"lucky": 23 },
    }

    assert complete_dict == {
        "base_url": "https://api.example.com",
        "url": "https://api.example.com/666/hail-satan",
        "method": "POST",
        "auto_coercion": True,
        "body": {"lucky": 23 },
        "brace_expansion": True
    }
