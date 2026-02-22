import pytest

from skivvy.verify import verify


def test_gt_passes():
    verify("$gt 5", 6)


def test_gt_fails_on_equal():
    with pytest.raises(Exception, match="Expected 6>6"):
        verify("$gt 6", 6)


def test_gt_requires_numeric_actual():
    with pytest.raises(Exception, match="Expected a number"):
        verify("$gt 1", "not-a-number")


def test_lt_passes():
    verify("$lt 10", 3)


def test_between_inclusive_bounds():
    verify("$between 1 3", 1)
    verify("$between 1 3", 3)


def test_between_out_of_range():
    with pytest.raises(Exception, match="between 1.0 and 3.0"):
        verify("$between 1 3", 4)


def test_between_lower_bound_must_not_exceed_upper():
    with pytest.raises(Exception, match="Lower bound"):
        verify("$between 5 1", 3)


def test_approximate_match_with_explicit_threshold_passes():
    verify("$~ 100 threshold 0.1", 108)


def test_approximate_match_with_explicit_threshold_fails():
    with pytest.raises(Exception, match="Expected 100.0"):
        verify("$~ 100 threshold 0.01", 103)


def test_len_match_supports_threshold_syntax():
    verify("$len ~10 threshold 0.2", "x" * 11)


def test_len_match_reports_error_for_non_sized_actual():
    with pytest.raises(Exception, match="has no len"):
        verify("$len 3", 123)
