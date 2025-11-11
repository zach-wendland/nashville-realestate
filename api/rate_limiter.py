"""Advanced rate limiting with adaptive backoff, token bucket, and intelligent retry.

This module implements sophisticated rate limiting strategies to maximize API throughput
while respecting provider limits and avoiding 429 errors.
"""
from __future__ import annotations

import logging
import random
import time
from collections import deque
from dataclasses import dataclass, field
from threading import Lock
from typing import Callable, Optional

import requests


@dataclass
class RateLimitConfig:
    """Configuration for adaptive rate limiter."""

    # Token bucket parameters
    tokens_per_second: float = 0.2  # For PRO plan: 1 request per 5 seconds
    max_tokens: int = 5  # Burst capacity

    # Backoff parameters
    base_backoff: float = 5.0  # Initial backoff on 429
    max_backoff: float = 60.0  # Maximum backoff time
    backoff_multiplier: float = 2.0  # Exponential multiplier
    jitter_factor: float = 0.1  # Random jitter to avoid thundering herd

    # Retry parameters
    max_retries: int = 5

    # Adaptive tuning
    adaptive: bool = True  # Auto-adjust based on 429 responses
    success_threshold: int = 10  # Successes before increasing rate
    failure_threshold: int = 2  # Failures before decreasing rate


class TokenBucket:
    """Token bucket algorithm for smooth rate limiting."""

    def __init__(self, rate: float, capacity: int):
        """
        Initialize token bucket.

        Args:
            rate: Tokens added per second
            capacity: Maximum tokens in bucket
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self.lock = Lock()

    def consume(self, tokens: int = 1, block: bool = True) -> bool:
        """
        Consume tokens from bucket.

        Args:
            tokens: Number of tokens to consume
            block: If True, wait for tokens; if False, return immediately

        Returns:
            True if tokens consumed, False if insufficient tokens
        """
        while True:
            with self.lock:
                now = time.time()
                elapsed = now - self.last_update

                # Refill tokens based on elapsed time
                self.tokens = min(
                    self.capacity,
                    self.tokens + elapsed * self.rate
                )
                self.last_update = now

                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True

                if not block:
                    return False

                # Calculate wait time for next token
                wait_time = (tokens - self.tokens) / self.rate

            # Wait outside the lock
            time.sleep(min(wait_time, 1.0))

    def get_wait_time(self, tokens: int = 1) -> float:
        """Get estimated wait time for tokens to be available."""
        with self.lock:
            if self.tokens >= tokens:
                return 0.0
            return (tokens - self.tokens) / self.rate


class AdaptiveRateLimiter:
    """Adaptive rate limiter that learns from API responses."""

    def __init__(self, config: Optional[RateLimitConfig] = None):
        """Initialize adaptive rate limiter."""
        self.config = config or RateLimitConfig()
        self.bucket = TokenBucket(
            rate=self.config.tokens_per_second,
            capacity=self.config.max_tokens
        )

        # Adaptive state
        self.consecutive_successes = 0
        self.consecutive_failures = 0
        self.current_backoff = self.config.base_backoff

        # Request history for analytics
        self.request_times = deque(maxlen=100)
        self.lock = Lock()

        logging.info(
            f"Initialized AdaptiveRateLimiter: "
            f"{self.config.tokens_per_second} req/s, "
            f"max burst={self.config.max_tokens}"
        )

    def _add_jitter(self, delay: float) -> float:
        """Add random jitter to delay to prevent thundering herd."""
        jitter = delay * self.config.jitter_factor
        return delay + random.uniform(-jitter, jitter)

    def _calculate_backoff(self, attempt: int) -> float:
        """Calculate exponential backoff with jitter."""
        backoff = min(
            self.config.base_backoff * (self.config.backoff_multiplier ** attempt),
            self.config.max_backoff
        )
        return self._add_jitter(backoff)

    def _adapt_rate(self, success: bool) -> None:
        """Adapt rate based on success/failure pattern."""
        if not self.config.adaptive:
            return

        with self.lock:
            if success:
                self.consecutive_successes += 1
                self.consecutive_failures = 0

                # After N successes, try increasing rate slightly
                if self.consecutive_successes >= self.config.success_threshold:
                    old_rate = self.bucket.rate
                    self.bucket.rate = min(
                        self.bucket.rate * 1.1,  # Increase by 10%
                        1.0  # Never exceed 1 req/sec
                    )
                    self.consecutive_successes = 0
                    logging.info(
                        f"Increased rate: {old_rate:.3f} → {self.bucket.rate:.3f} req/s"
                    )
            else:
                self.consecutive_failures += 1
                self.consecutive_successes = 0

                # After N failures, decrease rate
                if self.consecutive_failures >= self.config.failure_threshold:
                    old_rate = self.bucket.rate
                    self.bucket.rate *= 0.5  # Decrease by 50%
                    self.consecutive_failures = 0
                    logging.warning(
                        f"Decreased rate due to failures: {old_rate:.3f} → {self.bucket.rate:.3f} req/s"
                    )

    def execute_with_retry(
        self,
        func: Callable[[], requests.Response],
        operation_name: str = "API request"
    ) -> requests.Response:
        """
        Execute function with intelligent retry and rate limiting.

        Args:
            func: Function that makes the API request
            operation_name: Name for logging

        Returns:
            Response from successful request

        Raises:
            requests.HTTPError: If all retries exhausted
        """
        for attempt in range(self.config.max_retries):
            # Wait for token availability
            self.bucket.consume(tokens=1, block=True)

            # Record request time
            request_time = time.time()
            with self.lock:
                self.request_times.append(request_time)

            try:
                response = func()

                # Check for rate limiting
                if response.status_code == 429:
                    self._adapt_rate(success=False)

                    # Parse Retry-After header if available
                    retry_after = response.headers.get('Retry-After')
                    if retry_after:
                        try:
                            wait_time = float(retry_after)
                        except ValueError:
                            wait_time = self._calculate_backoff(attempt)
                    else:
                        wait_time = self._calculate_backoff(attempt)

                    logging.warning(
                        f"{operation_name} rate limited (429), "
                        f"waiting {wait_time:.1f}s (attempt {attempt + 1}/{self.config.max_retries})"
                    )
                    time.sleep(wait_time)
                    continue

                # Success
                response.raise_for_status()
                self._adapt_rate(success=True)
                return response

            except requests.HTTPError as e:
                if e.response and e.response.status_code == 429:
                    # Already handled above
                    continue
                # Other HTTP errors
                logging.error(f"{operation_name} failed: {e}")
                raise

            except requests.RequestException as e:
                # Network errors
                if attempt < self.config.max_retries - 1:
                    wait_time = self._calculate_backoff(attempt)
                    logging.warning(
                        f"{operation_name} network error: {e}, "
                        f"retrying in {wait_time:.1f}s"
                    )
                    time.sleep(wait_time)
                    continue
                raise

        # All retries exhausted
        raise requests.HTTPError(
            f"{operation_name} failed after {self.config.max_retries} attempts"
        )

    def get_stats(self) -> dict:
        """Get rate limiter statistics."""
        with self.lock:
            now = time.time()
            recent_requests = [
                t for t in self.request_times
                if now - t < 60  # Last minute
            ]

            return {
                "current_rate": self.bucket.rate,
                "available_tokens": self.bucket.tokens,
                "max_tokens": self.bucket.capacity,
                "requests_last_minute": len(recent_requests),
                "consecutive_successes": self.consecutive_successes,
                "consecutive_failures": self.consecutive_failures,
            }


# Global rate limiter instance
_global_limiter: Optional[AdaptiveRateLimiter] = None
_limiter_lock = Lock()


def get_rate_limiter(config: Optional[RateLimitConfig] = None) -> AdaptiveRateLimiter:
    """Get or create global rate limiter instance."""
    global _global_limiter

    with _limiter_lock:
        if _global_limiter is None:
            _global_limiter = AdaptiveRateLimiter(config)
        return _global_limiter


def reset_rate_limiter() -> None:
    """Reset global rate limiter (for testing)."""
    global _global_limiter
    with _limiter_lock:
        _global_limiter = None
