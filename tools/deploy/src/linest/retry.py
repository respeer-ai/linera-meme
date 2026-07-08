"""Retry policy for transient CLI failures."""

from __future__ import annotations

import random
import time
from typing import Callable, TypeVar

from linest.errors import LineraCliError

T = TypeVar("T")


class RetryPolicy:
    """Retry a callable when a transient linera CLI error is detected."""

    # Substrings that indicate the failure may be resolved by retrying.
    _DEFAULT_RETRYABLE_SUBSTRINGS = (
        "A different block was already committed",
        "Client failed to propose block",
        "Timeout",
        "timed out",
        "Connection refused",
    )

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 10.0,
        retryable_substrings: tuple[str, ...] | None = None,
        jitter: bool = True,
    ) -> None:
        self.max_attempts = max(1, max_attempts)
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.retryable_substrings = (
            retryable_substrings or self._DEFAULT_RETRYABLE_SUBSTRINGS
        )
        self.jitter = jitter

    def call(self, callable_: Callable[[], T]) -> T:
        """Invoke ``callable_`` and retry on transient errors."""
        last_error: LineraCliError | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                return callable_()
            except LineraCliError as error:
                last_error = error
                if attempt == self.max_attempts or not self._is_retryable(error):
                    raise
                self._sleep(self._delay_for_attempt(attempt))

        # Unreachable, but kept for type safety.
        raise last_error or LineraCliError("Retry loop exhausted")

    def _is_retryable(self, error: LineraCliError) -> bool:
        message = str(error)
        return any(substring in message for substring in self.retryable_substrings)

    def _delay_for_attempt(self, attempt: int) -> float:
        delay = self.base_delay * (2 ** (attempt - 1))
        delay = min(delay, self.max_delay)
        if self.jitter:
            delay *= 0.5 + random.random() * 0.5
        return delay

    def _sleep(self, seconds: float) -> None:
        time.sleep(seconds)
