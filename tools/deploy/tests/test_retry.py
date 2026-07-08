"""Tests for RetryPolicy."""

from unittest.mock import MagicMock, patch

import pytest

from linest.errors import LineraCliError
from linest.retry import RetryPolicy


def test_retry_policy_succeeds_without_retries() -> None:
    policy = RetryPolicy(max_attempts=3)
    mock = MagicMock(return_value="ok")

    with patch.object(policy, "_sleep"):
        result = policy.call(mock)

    assert result == "ok"
    assert mock.call_count == 1


def test_retry_policy_retries_on_transient_error() -> None:
    policy = RetryPolicy(max_attempts=3)
    error = LineraCliError(
        "linera command failed: ...\nA different block was already committed"
    )
    mock = MagicMock(side_effect=[error, error, "ok"])

    with patch.object(policy, "_sleep"):
        result = policy.call(mock)

    assert result == "ok"
    assert mock.call_count == 3


def test_retry_policy_gives_up_after_max_attempts() -> None:
    policy = RetryPolicy(max_attempts=2)
    error = LineraCliError(
        "linera command failed: ...\nA different block was already committed"
    )
    mock = MagicMock(side_effect=[error, error, error])

    with patch.object(policy, "_sleep"):
        with pytest.raises(LineraCliError):
            policy.call(mock)

    assert mock.call_count == 2


def test_retry_policy_does_not_retry_fatal_error() -> None:
    policy = RetryPolicy(max_attempts=3)
    error = LineraCliError("linera command failed: ...\nInvalid module")
    mock = MagicMock(side_effect=[error, "ok"])

    with patch.object(policy, "_sleep"):
        with pytest.raises(LineraCliError, match="Invalid module"):
            policy.call(mock)

    assert mock.call_count == 1


def test_retry_policy_uses_custom_substrings() -> None:
    policy = RetryPolicy(
        max_attempts=2, retryable_substrings=("custom transient",)
    )
    error = LineraCliError("linera command failed: ...\ncustom transient")
    mock = MagicMock(side_effect=[error, "ok"])

    with patch.object(policy, "_sleep"):
        result = policy.call(mock)

    assert result == "ok"
    assert mock.call_count == 2
