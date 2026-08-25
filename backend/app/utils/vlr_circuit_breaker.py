"""
Circuit breaker for calls to the unofficial VLR.gg API.

When the VLR API is down or returning errors, the circuit breaker
prevents cascading failures by short-circuiting calls and allowing
periodic probes to test if the API has recovered.

State machine: CLOSED → (threshold failures) → OPEN → (timeout) → HALF_OPEN → (success) → CLOSED
"""
import time
import logging
from typing import Optional, Callable, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Default configuration — tunable per environment
_DEFAULT_FAILURE_THRESHOLD = 5        # consecutive failures to trip
_DEFAULT_RECOVERY_TIMEOUT = 60.0      # seconds before half-open probe
_DEFAULT_HALF_OPEN_MAX_TRIES = 3      # probes before fully resetting


class CircuitBreaker:
    """A simple in-process circuit breaker with half-open probing."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = _DEFAULT_FAILURE_THRESHOLD,
        recovery_timeout: float = _DEFAULT_RECOVERY_TIMEOUT,
        half_open_max_tries: int = _DEFAULT_HALF_OPEN_MAX_TRIES,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_tries = half_open_max_tries

        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._state: str = "CLOSED"          # CLOSED | OPEN | HALF_OPEN
        self._half_open_successes = 0

    @property
    def state(self) -> str:
        """Current circuit state (CLOSED, OPEN, or HALF_OPEN)."""
        self._transition()
        return self._state

    @property
    def is_open(self) -> bool:
        """True if the circuit is OPEN (requests should be short-circuited)."""
        return self.state == "OPEN"

    def _transition(self) -> None:
        """Check if the circuit should transition based on timeouts."""
        if self._state == "OPEN" and self._failure_count > 0:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self.recovery_timeout:
                self._state = "HALF_OPEN"
                self._half_open_successes = 0
                logger.info(
                    "Circuit [%s] transitioning OPEN → HALF_OPEN (elapsed %.1fs)",
                    self.name, elapsed,
                )

    def record_success(self) -> None:
        """Record a successful call through the circuit."""
        if self._state == "HALF_OPEN":
            self._half_open_successes += 1
            if self._half_open_successes >= self.half_open_max_tries:
                self._state = "CLOSED"
                self._failure_count = 0
                logger.info("Circuit [%s] reset to CLOSED after half-open successes", self.name)
        else:
            # CLOSED: reset failure counter on success
            self._failure_count = 0

    def record_failure(self) -> None:
        """Record a failed call through the circuit."""
        self._last_failure_time = time.monotonic()
        if self._state == "HALF_OPEN":
            self._state = "OPEN"
            logger.warning("Circuit [%s] tripped back to OPEN (half-open failure)", self.name)
        else:
            # CLOSED: accumulate failures
            self._failure_count += 1
            if self._failure_count >= self.failure_threshold:
                self._state = "OPEN"
                logger.warning(
                    "Circuit [%s] OPEN after %d consecutive failures",
                    self.name, self._failure_count,
                )

    def call(self, fn: Callable[[], T], fallback: Optional[Callable[[], T]] = None) -> Optional[T]:
        """
        Execute `fn` through the circuit breaker.

        If the circuit is OPEN, the call is skipped and `fallback` is invoked
        (if provided). In HALF_OPEN state, a single probe request is allowed.

        Returns:
            The result of `fn` or `fallback`, or None if no fallback and circuit open.
        """
        self._transition()

        if self._state == "OPEN":
            logger.debug("Circuit [%s] is OPEN — short-circuiting call", self.name)
            if fallback:
                return fallback()
            return None

        try:
            result = fn()
            self.record_success()
            return result
        except Exception:
            self.record_failure()
            if fallback:
                return fallback()
            raise


# Global circuits for different VLR endpoints
vlr_upcoming_circuit = CircuitBreaker("vlr_upcoming", failure_threshold=5, recovery_timeout=120.0)
vlr_live_score_circuit = CircuitBreaker("vlr_live_score", failure_threshold=3, recovery_timeout=60.0)
vlr_match_page_circuit = CircuitBreaker("vlr_match_page", failure_threshold=3, recovery_timeout=60.0)