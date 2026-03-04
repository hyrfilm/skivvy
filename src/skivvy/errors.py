class ExpectedTestFailure(Exception):
    """Base class for expected assertion-like test failures."""


class VerificationFailure(ExpectedTestFailure):
    """Raised when expected and actual verification does not match."""

