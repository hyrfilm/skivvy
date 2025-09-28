import json
from functools import partial

import pytest

from skivvy.matchers import file_writer
from skivvy.test_runner import auto_coercer
from skivvy.util import scope, file_util, dict_util
from skivvy.brace_expansion import brace_expand_string
from . import test_util

default_files = {
    "user_id.txt": "123",
    "dashboard.txt": "dashboard/user",
}

@pytest.fixture()
def tmp_files():
    for filename, content in default_files.items():
        file_writer(filename, content)
    yield default_files
    file_util.cleanup_tmp_files(warn=False, throw=False)

def test_simple_expansion(tmp_files):
    assert brace_expand_string("<user_id.txt>") == "123"
    assert brace_expand_string("<user_id.txt>", auto_coerce_func=auto_coercer) == 123

def test_compound_expansion(tmp_files):
    assert "www.example.com/dashboard/user/123" == brace_expand_string("www.example.com/<dashboard.txt>/<user_id.txt>", auto_coerce=True)

def test_brace_expansion_with_variables():
    file_util.set_current_file("./login_tests/1_login.json")
    # here we basically simulate using $store and $fetch which allow for storing variables
    # in memory that are scoped to the directory you"re in. Generally better than using $write_file etc
    scope.store("email", "dude@lebowski.com")
    scope.store("password", "s3cr3t")
    scope.store("user_id", "1234")
    scope.store("session", "56789")
    scope.store("url", "https://api.example.com")

    template = { "url": "<url>/login/<user_id>?q=<session>", "body": { "email": "<email>", "password": "<password>" }}
    request = test_util.json_transform_str(template, brace_expand_string)
    expected = {
        "url": "https://api.example.com/login/1234?q=56789",
        "body": {"email": "dude@lebowski.com", "password": "s3cr3t"},
    }
    assert json.loads(request) == expected

    # since we are not changing dir these variables should still be in scope
    file_util.set_current_file("./login_tests/2_logout.json")
    brace_expand_coerce = partial(brace_expand_string, auto_coerce_func=auto_coercer)
    d = { "url": "<URL>/logout", "integer": "<session>", "should-be-ignored": "<>email<>url<>session" }
    data = dict_util.map_nested_dicts_py(d, brace_expand_coerce)
    expected ='{"url": "https://api.example.com/logout", "integer": 56789, "should-be-ignored": "<>email<>url<>session"}'
    assert json.dumps(data) == expected

    # should result in a new scope
    file_util.set_current_file("./new_scope/2_logout.json")
    # no values should change so should be equal to itself
    new_dict = { "a": "<url>", "b": "<session>", "c": "<session>" }
    assert dict_util.map_nested_dicts_py(new_dict, brace_expand_string) == new_dict
    # set some variables in the new scope
    scope.store("email", "dude@example.com")
    scope.store("session", "666")

    expected = '{"a":"dude@example.com","b":"666"}'
    assert test_util.json_transform_str({ "a": "<email>", "b": "<session>" }, brace_expand_string) == expected


