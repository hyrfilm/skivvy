import textwrap

import pytest

from skivvy import custom_matchers, matchers


def write_matcher_file(tmp_path, name, source):
    path = tmp_path / f"{name}.py"
    path.write_text(textwrap.dedent(source))
    return path


def test_custom_matcher_bool_result_is_normalized_to_tuple(tmp_path):
    source = write_matcher_file(
        tmp_path,
        "always_true",
        """
        def match(expected, actual):
            return True
        """,
    )

    matcher = custom_matchers.CustomMatcher(str(source))

    assert matcher.match(" expected ", {"x": 1}) == (True, "")


def test_custom_matcher_tuple_result_is_passed_through(tmp_path):
    source = write_matcher_file(
        tmp_path,
        "tuple_result",
        """
        def match(expected, actual):
            return False, "no match"
        """,
    )

    matcher = custom_matchers.CustomMatcher(str(source))

    assert matcher.match("x", "y") == (False, "no match")


def test_custom_matcher_missing_match_function_fails_to_load(tmp_path):
    source = write_matcher_file(
        tmp_path,
        "missing_match",
        """
        def not_match(expected, actual):
            return True
        """,
    )

    with pytest.raises(AssertionError, match="Failed to load matcher"):
        custom_matchers.CustomMatcher(str(source))


def test_custom_matcher_wrong_signature_fails_to_load(tmp_path):
    source = write_matcher_file(
        tmp_path,
        "wrong_signature",
        """
        def match(expected):
            return True
        """,
    )

    with pytest.raises(AssertionError, match="Expected 'match' to take exactly 2 parameters"):
        custom_matchers.CustomMatcher(str(source))


def test_custom_matcher_invalid_result_type_is_wrapped(tmp_path):
    source = write_matcher_file(
        tmp_path,
        "invalid_result",
        """
        def match(expected, actual):
            return "nope"
        """,
    )

    matcher = custom_matchers.CustomMatcher(str(source))

    with pytest.raises(Exception, match="Custom matcher threw unexpected execption"):
        matcher.match("x", "y")


def test_custom_matcher_exception_is_wrapped(tmp_path):
    source = write_matcher_file(
        tmp_path,
        "raises_error",
        """
        def match(expected, actual):
            raise RuntimeError("boom")
        """,
    )

    matcher = custom_matchers.CustomMatcher(str(source))

    with pytest.raises(Exception, match="Custom matcher threw unexpected execption: boom"):
        matcher.match("x", "y")


def test_load_registers_custom_matchers_from_directory(tmp_path, isolated_matcher_state):
    plugins_dir = tmp_path / "plugins"
    plugins_dir.mkdir()
    write_matcher_file(
        plugins_dir,
        "is_hello",
        """
        def match(expected, actual):
            return actual == "hello", "expected hello"
        """,
    )

    custom_matchers.load({"matchers": str(plugins_dir)})

    assert "$is_hello" in matchers.matcher_dict
    assert matchers.matcher_dict["$is_hello"]("", "hello") == (True, "expected hello")


def test_load_without_matchers_dir_is_noop(isolated_matcher_state):
    before = dict(matchers.matcher_dict)

    custom_matchers.load({})

    assert matchers.matcher_dict == before
