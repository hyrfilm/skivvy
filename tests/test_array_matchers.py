"""Tests for matcher syntax used inside array elements."""
import pytest

from skivvy.verify import verify


# --- Matchers on plain values inside arrays ---

def test_matcher_on_scalar_in_array_passes():
    # $between matcher applied to a scalar element in an array
    verify(["$between 1 3"], [1, 2, 3])


def test_matcher_on_scalar_in_array_no_match_fails():
    with pytest.raises(Exception, match="Didn't find"):
        verify(["$between 10 20"], [1, 2, 3])


def test_gt_matcher_on_scalar_in_array():
    verify(["$gt 0"], [1, 2, 3])


def test_gt_matcher_on_scalar_in_array_fails():
    with pytest.raises(Exception, match="Didn't find"):
        verify(["$gt 100"], [1, 2, 3])


def test_contains_matcher_on_string_in_array():
    verify(["$contains hello"], ["hello world", "foo", "bar"])


def test_contains_matcher_on_string_no_match_fails():
    with pytest.raises(Exception, match="Didn't find"):
        verify(["$contains xyz"], ["hello world", "foo", "bar"])


# --- Matchers on dict fields inside arrays (without match_subsets) ---

def test_matcher_in_dict_field_in_array_passes():
    # Any element with id between 1 and 3 — no match_subsets needed
    verify(
        [{"id": "$between 1 3"}],
        [{"id": 1}, {"id": 2}, {"id": 3}],
    )


def test_matcher_in_dict_field_in_array_only_one_element_matches():
    # Only the element with id=2 satisfies $between 2 2
    verify(
        [{"id": "$between 2 2"}],
        [{"id": 1}, {"id": 2}, {"id": 3}],
    )


def test_matcher_in_dict_field_in_array_fails_when_no_element_matches():
    with pytest.raises(Exception, match="Didn't find"):
        verify(
            [{"id": "$between 10 20"}],
            [{"id": 1}, {"id": 2}, {"id": 3}],
        )


def test_multiple_matcher_entries_each_need_a_match():
    # Two expected entries: first needs id in [1,3], second needs id in [5,7]
    verify(
        [{"id": "$between 1 3"}, {"id": "$between 5 7"}],
        [{"id": 2}, {"id": 6}],
    )


def test_multiple_matcher_entries_fails_if_one_has_no_match():
    with pytest.raises(Exception, match="Didn't find"):
        verify(
            [{"id": "$between 1 3"}, {"id": "$between 50 60"}],
            [{"id": 2}, {"id": 6}],
        )


# --- Matchers in dict fields inside arrays with match_subsets ---

def test_matcher_in_dict_field_with_match_subsets_passes():
    # With match_subsets, expected dict is partial — extra actual fields are allowed
    verify(
        [{"id": "$between 1 3"}],
        [{"id": 1, "name": "Alice"}, {"id": 5, "name": "Bob"}],
        match_subsets=True,
    )


def test_matcher_in_dict_field_with_match_subsets_fails_when_no_match():
    with pytest.raises(Exception, match="Didn't find"):
        verify(
            [{"id": "$between 10 20"}],
            [{"id": 1, "name": "Alice"}, {"id": 5, "name": "Bob"}],
            match_subsets=True,
        )


# --- match_every_entry: template must hold for all actual entries ---

def test_match_every_entry_passes_when_all_match():
    verify(
        [{"rating": "$between 1 5"}],
        [{"rating": 1}, {"rating": 3}, {"rating": 5}],
        match_every_entry=True,
    )


def test_match_every_entry_fails_when_one_does_not_match():
    with pytest.raises(Exception):
        verify(
            [{"rating": "$between 1 5"}],
            [{"rating": 1}, {"rating": 3}, {"rating": 9}],
            match_every_entry=True,
        )


def test_match_every_entry_on_scalars():
    verify(
        ["$gt 0"],
        [1, 2, 3],
        match_every_entry=True,
    )


def test_match_every_entry_on_scalars_fails():
    with pytest.raises(Exception):
        verify(
            ["$gt 0"],
            [1, -1, 3],
            match_every_entry=True,
        )


def test_match_every_entry_combined_with_match_subsets():
    # Partial dict matching + every entry must satisfy it
    verify(
        [{"active": True}],
        [{"id": 1, "active": True}, {"id": 2, "active": True}],
        match_every_entry=True,
        match_subsets=True,
    )


def test_match_every_entry_combined_with_match_subsets_fails():
    with pytest.raises(Exception):
        verify(
            [{"active": True}],
            [{"id": 1, "active": True}, {"id": 2, "active": False}],
            match_every_entry=True,
            match_subsets=True,
        )


def test_match_every_entry_missing_subset_key_fails_by_default():
    with pytest.raises(Exception):
        verify(
            [{"score": "$gt 0"}],
            [{"name": "Alice", "score": 42}, {"name": "Bob"}],
            match_every_entry=True,
            match_subsets=True,
        )


def test_match_every_entry_empty_object_can_be_skipped():
    verify(
        [{"score": "$gt 0"}],
        [{"score": 42}, {}],
        match_every_entry=True,
        match_subsets=True,
        skip_empty_objects=True,
    )


def test_match_every_entry_non_empty_disjoint_object_is_not_skipped():
    with pytest.raises(Exception):
        verify(
            [{"a": 1}],
            [{"b": 2}],
            match_every_entry=True,
            match_subsets=True,
            skip_empty_objects=True,
        )


def test_match_every_entry_empty_array_can_be_skipped():
    verify(
        [[1]],
        [[1], []],
        match_every_entry=True,
        match_subsets=True,
        skip_empty_arrays=True,
    )


# --- Regression: existing exact and subset matching still works ---

def test_exact_scalar_in_array_still_works():
    verify([1, 2], [1, 2, 3])


def test_exact_dict_in_array_still_works():
    verify([{"id": 1}], [{"id": 1}, {"id": 2}])


def test_exact_dict_in_array_fails_when_missing():
    with pytest.raises(Exception, match="Didn't find"):
        verify([{"id": 99}], [{"id": 1}, {"id": 2}])


def test_match_subsets_partial_dict_still_works():
    verify(
        [{"postId": 1}],
        [{"postId": 1, "id": 1, "email": "a@b.com"}],
        match_subsets=True,
    )
