"""Tests for CircuitBreaker implementation"""

import pytest
import time
from etl.rate_limiter import CircuitBreaker


def test_circuit_breaker_opens_after_failures():
    cb = CircuitBreaker(failure_threshold=2, timeout=1)

    def failing_fn():
        raise Exception("API call failed")

    with pytest.raises(Exception):
        cb.call(failing_fn)

    with pytest.raises(Exception):
        cb.call(failing_fn)

    with pytest.raises(Exception):
        cb.call(failing_fn)


def test_circuit_breaker_allows_recovery():
    cb = CircuitBreaker(failure_threshold=2, timeout=1)

    call_count = 0

    def failing_fn():
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            raise Exception("API call failed")
        return "success"

    with pytest.raises(Exception):
        cb.call(failing_fn)

    with pytest.raises(Exception):
        cb.call(failing_fn)

    time.sleep(1.5)

    result = cb.call(failing_fn)
    assert result == "success"


def test_circuit_breaker_states():
    cb = CircuitBreaker(failure_threshold=2, timeout=1)

    def failing_fn():
        raise Exception("fail")

    assert cb.state == "CLOSED"

    with pytest.raises(Exception):
        cb.call(failing_fn)

    with pytest.raises(Exception):
        cb.call(failing_fn)

    assert cb.state == "OPEN"

    time.sleep(1.5)

    with pytest.raises(Exception):
        cb.call(failing_fn)

    assert cb.state == "HALF_OPEN"