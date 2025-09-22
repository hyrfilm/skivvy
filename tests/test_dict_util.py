import pytest

from skivvy.util.dict_util import subset, map_nested_dicts_py, get_all


def test_subset_basic():
    d = {"a": 1, "b": 2, "c": 3}
    # includes an existing and a non-existing key
    result = subset(d, ["a", "x"])
    assert result == {"a": 1}


def test_map_nested_dicts_py_numbers():
    d = {
        "x": 1,
        "y": {"y1": 2, "y2": {"y21": 3}},
        "z": 4,
    }

    def times_two(v):
        return v * 2

    result = map_nested_dicts_py(d, times_two)
    assert result == {
        "x": 2,
        "y": {"y1": 4, "y2": {"y21": 6}},
        "z": 8,
    }


def test_get_many_returns_tuple():
    d = {"a": 10, "b": 20, "c": 30}
    values = get_all(d, "a", "c")
    assert values == (10, 30)
    values = get_all(d, "a")
    assert values == (10,)
    values = get_all(d)
    assert values == ()


def test_get_many_raises_keyerror_if_key_not_found():
    d = {"a": 1}
    with pytest.raises(KeyError):
        _ = get_all(d, "dude!")
