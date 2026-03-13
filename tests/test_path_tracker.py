import pytest

from skivvy import matchers
from skivvy.path_tracker import PathTracker


@pytest.fixture(autouse=True)
def reset_path(monkeypatch):
    monkeypatch.setattr(matchers, "_path", PathTracker())


# --- PathTracker class ---

def test_starts_empty():
    tracker = PathTracker()
    assert tracker.current == []


def test_push_adds_segment():
    tracker = PathTracker()
    tracker.push("a")
    assert tracker.current == ["a"]


def test_push_integer_index():
    tracker = PathTracker()
    tracker.push(0)
    assert tracker.current == [0]


def test_pop_removes_last_segment():
    tracker = PathTracker()
    tracker.push("a")
    tracker.push("b")
    tracker.pop()
    assert tracker.current == ["a"]


def test_current_returns_copy():
    tracker = PathTracker()
    tracker.push("a")
    snapshot = tracker.current
    tracker.push("b")
    assert snapshot == ["a"]



def test_nested_dict_and_list_traversal():
    # Simulates traversing {"response": {"items": [{"id": "..."}]}}
    tracker = PathTracker()

    tracker.push("response")
    tracker.push("items")
    tracker.push(0)
    tracker.push("id")
    assert tracker.current == ["response", "items", 0, "id"]
    tracker.pop()  # leave "id"

    tracker.pop()  # leave index 0
    tracker.push(1)
    tracker.push("id")
    assert tracker.current == ["response", "items", 1, "id"]
    tracker.pop()
    tracker.pop()

    tracker.pop()  # leave "items"
    tracker.pop()  # leave "response"
    assert tracker.current == []


# --- Module-level functions ---

def test_push_path_and_get_path():
    matchers.push_path("a")
    matchers.push_path(0)
    assert matchers.get_path() == ["a", 0]


def test_pop_path_removes_last():
    matchers.push_path("a")
    matchers.push_path("b")
    matchers.pop_path()
    assert matchers.get_path() == ["a"]
