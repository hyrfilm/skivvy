import pytest

from skivvy import matchers
from skivvy.path_tracker import PathTracker
from skivvy.verify import verify


@pytest.fixture(autouse=True)
def reset_matchers(monkeypatch):
    monkeypatch.setattr(matchers, "_matcher_state", {})
    monkeypatch.setattr(matchers, "_path", PathTracker())


# --- $unique ---

def test_unique_passes_for_distinct_values():
    matchers.push_path("items")
    matchers.push_path(0)
    matchers.push_path("id")
    assert matchers.match_unique("", 1) == (True, matchers.SUCCESS_MSG)
    matchers.pop_path()
    matchers.pop_path()
    matchers.push_path(1)
    matchers.push_path("id")
    assert matchers.match_unique("", 2) == (True, matchers.SUCCESS_MSG)


def test_unique_fails_for_duplicate_value():
    matchers.push_path("items")
    matchers.push_path(0)
    matchers.push_path("id")
    matchers.match_unique("", 42)
    matchers.pop_path()
    matchers.pop_path()
    matchers.push_path(1)
    matchers.push_path("id")
    result, msg = matchers.match_unique("", 42)
    assert result is False
    assert "42" in msg


def test_unique_integration():
    verify(
        [{"id": "$unique"}],
        [{"id": 1}, {"id": 2}, {"id": 3}],
        match_every_entry=True,
    )


def test_unique_integration_fails_on_duplicate():
    with pytest.raises(Exception, match="Duplicate"):
        verify(
            [{"id": "$unique"}],
            [{"id": 1}, {"id": 2}, {"id": 1}],
            match_every_entry=True,
        )


# --- $asc ---

def test_asc_passes_for_ascending_numbers():
    matchers.push_path("items")
    matchers.push_path(0)
    matchers.push_path("score")
    matchers.match_asc("", 1)
    matchers.pop_path()
    matchers.pop_path()
    matchers.push_path(1)
    matchers.push_path("score")
    assert matchers.match_asc("", 2) == (True, matchers.SUCCESS_MSG)


def test_asc_fails_for_non_ascending_number():
    matchers.push_path("items")
    matchers.push_path(0)
    matchers.push_path("score")
    matchers.match_asc("", 5)
    matchers.pop_path()
    matchers.pop_path()
    matchers.push_path(1)
    matchers.push_path("score")
    result, msg = matchers.match_asc("", 3)
    assert result is False
    assert "ascending" in msg


def test_asc_passes_for_ascending_strings():
    matchers.push_path("items")
    matchers.push_path(0)
    matchers.push_path("name")
    matchers.match_asc("", "apple")
    matchers.pop_path()
    matchers.pop_path()
    matchers.push_path(1)
    matchers.push_path("name")
    assert matchers.match_asc("", "banana") == (True, matchers.SUCCESS_MSG)


def test_asc_integration():
    verify(
        [{"score": "$asc"}],
        [{"score": 1}, {"score": 2}, {"score": 3}],
        match_every_entry=True,
    )


def test_asc_integration_fails_on_out_of_order():
    with pytest.raises(Exception, match="ascending"):
        verify(
            [{"score": "$asc"}],
            [{"score": 1}, {"score": 3}, {"score": 2}],
            match_every_entry=True,
        )


# --- $desc ---

def test_desc_passes_for_descending_numbers():
    matchers.push_path("items")
    matchers.push_path(0)
    matchers.push_path("score")
    matchers.match_desc("", 10)
    matchers.pop_path()
    matchers.pop_path()
    matchers.push_path(1)
    matchers.push_path("score")
    assert matchers.match_desc("", 5) == (True, matchers.SUCCESS_MSG)


def test_desc_fails_for_non_descending_number():
    matchers.push_path("items")
    matchers.push_path(0)
    matchers.push_path("score")
    matchers.match_desc("", 5)
    matchers.pop_path()
    matchers.pop_path()
    matchers.push_path(1)
    matchers.push_path("score")
    result, msg = matchers.match_desc("", 10)
    assert result is False
    assert "descending" in msg


def test_desc_integration():
    verify(
        [{"score": "$desc"}],
        [{"score": 3}, {"score": 2}, {"score": 1}],
        match_every_entry=True,
    )


def test_desc_integration_fails_on_out_of_order():
    with pytest.raises(Exception, match="descending"):
        verify(
            [{"score": "$desc"}],
            [{"score": 3}, {"score": 1}, {"score": 2}],
            match_every_entry=True,
        )
