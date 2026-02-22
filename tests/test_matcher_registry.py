import pytest

from skivvy import matchers


@pytest.fixture
def minimal_registry(monkeypatch):
    registry = {
        "$pass": lambda expected, actual: (True, "ok"),
        "$fail": lambda expected, actual: (False, "nope"),
    }
    monkeypatch.setattr(matchers, "matcher_dict", dict(registry))
    return matchers.matcher_dict


def test_add_matcher_registers_with_dollar_prefix(isolated_matcher_state):
    def custom(expected, actual):
        return True, "OK"

    matchers.add_matcher("custom", custom)

    assert "$custom" in matchers.matcher_dict
    assert matchers.matcher_dict["$custom"] is custom


def test_add_matcher_rejects_duplicate_public_name(isolated_matcher_state):
    def first(expected, actual):
        return True, "OK"

    def second(expected, actual):
        return True, "OK"

    matchers.add_matcher("dup", first)

    with pytest.raises(AssertionError, match="Duplicate matcher: dup"):
        matchers.add_matcher("dup", second)


def test_add_negating_matchers_adds_wrappers_and_flips_results(minimal_registry):
    matchers.add_negating_matchers()

    assert "$!pass" in matchers.matcher_dict
    assert "$!fail" in matchers.matcher_dict

    ok_result, ok_msg = matchers.matcher_dict["$!fail"]("", "anything")
    assert (ok_result, ok_msg) == (True, None)

    fail_result, fail_msg = matchers.matcher_dict["$!pass"]("x", "y")
    assert fail_result is False
    assert "negating matcher" in fail_msg
    assert "$!pass x" in fail_msg


def test_add_negating_matchers_is_idempotent(minimal_registry):
    matchers.add_negating_matchers()
    first_keys = set(matchers.matcher_dict.keys())

    matchers.add_negating_matchers()

    assert set(matchers.matcher_dict.keys()) == first_keys
    assert "$!!pass" not in matchers.matcher_dict
    assert "$!!fail" not in matchers.matcher_dict


def test_get_matcher_options_self_returns_options_for_calling_matcher(isolated_matcher_state):
    seen = {}

    def custom(expected, actual):
        seen["opts"] = matchers.get_matcher_options_self()
        return True, "OK"

    matchers.add_matcher("opts_demo", custom)
    matchers.set_matcher_options({"$opts_demo": {"replace": {"a": "b"}}})

    result, _ = matchers.matcher_dict["$opts_demo"]("", "")

    assert result is True
    assert seen["opts"] == {"replace": {"a": "b"}}
