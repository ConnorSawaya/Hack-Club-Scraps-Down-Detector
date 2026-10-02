import threading
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import requests

from status_probe import (
    MIN_REQUEST_INTERVAL_SECONDS,
    REQUEST_HEADERS,
    REQUEST_TIMEOUT_SECONDS,
    SCRAPS_URL,
    StatusProbe,
)


class FakeClock:
    def __init__(self):
        self.elapsed = 0.0
        self.start = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)

    def monotonic(self):
        return self.elapsed

    def wall_time(self):
        return self.start + timedelta(seconds=self.elapsed)

    def advance(self, seconds):
        self.elapsed += seconds


class StatusProbeTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.probe = StatusProbe(
            monotonic=self.clock.monotonic,
            wall_clock=self.clock.wall_time,
        )

    def test_requests_fixed_target_with_bounded_timeout(self):
        requester = Mock(return_value=SimpleNamespace(status_code=200))

        result = self.probe.check(requester)

        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.checked_at, self.clock.start)
        requester.assert_called_once_with(
            SCRAPS_URL,
            headers=REQUEST_HEADERS,
            timeout=REQUEST_TIMEOUT_SECONDS,
            allow_redirects=False,
        )

    def test_result_is_shared_for_all_calls_within_interval(self):
        requester = Mock(return_value=SimpleNamespace(status_code=200))

        first = self.probe.check(requester)
        second = self.probe.check(requester)
        self.clock.advance(MIN_REQUEST_INTERVAL_SECONDS - 1)
        third = self.probe.check(requester)

        self.assertIs(first, second)
        self.assertIs(first, third)
        requester.assert_called_once()

    def test_new_request_is_allowed_at_interval_boundary(self):
        requester = Mock(side_effect=[SimpleNamespace(status_code=200), SimpleNamespace(status_code=503)])

        first = self.probe.check(requester)
        self.clock.advance(MIN_REQUEST_INTERVAL_SECONDS)
        second = self.probe.check(requester)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 503)
        self.assertEqual(requester.call_count, 2)

    def test_non_200_response_is_cached(self):
        requester = Mock(return_value=SimpleNamespace(status_code=503))

        first = self.probe.check(requester)
        second = self.probe.check(requester)

        self.assertEqual(first.status_code, 503)
        self.assertIs(first, second)
        requester.assert_called_once()

    def test_timeout_is_safe_and_cached_until_interval_expires(self):
        requester = Mock(side_effect=[requests.Timeout(), SimpleNamespace(status_code=200)])

        timed_out = self.probe.check(requester)
        cached_timeout = self.probe.check(requester)
        self.clock.advance(MIN_REQUEST_INTERVAL_SECONDS)
        recovered = self.probe.check(requester)

        self.assertIsNone(timed_out.status_code)
        self.assertEqual(timed_out.error, "timeout")
        self.assertIs(timed_out, cached_timeout)
        self.assertEqual(recovered.status_code, 200)
        self.assertEqual(requester.call_count, 2)

    def test_connection_error_is_safe_and_cached(self):
        requester = Mock(side_effect=requests.ConnectionError("private details"))

        first = self.probe.check(requester)
        second = self.probe.check(requester)

        self.assertIsNone(first.status_code)
        self.assertEqual(first.error, "request")
        self.assertIs(first, second)
        requester.assert_called_once()

    def test_unexpected_error_does_not_escape_to_the_ui(self):
        requester = Mock(side_effect=RuntimeError("internal details"))

        with self.assertLogs("status_probe", level="ERROR") as logged:
            result = self.probe.check(requester)

        self.assertIsNone(result.status_code)
        self.assertEqual(result.error, "unexpected")
        self.assertNotIn("internal details", str(result))
        self.assertNotIn("internal details", " ".join(logged.output))

    def test_concurrent_sessions_share_one_in_flight_request(self):
        entered = threading.Event()
        release = threading.Event()
        call_count = 0
        call_lock = threading.Lock()
        results = []

        def slow_requester(url, **kwargs):
            nonlocal call_count
            with call_lock:
                call_count += 1
            entered.set()
            release.wait(timeout=2)
            return SimpleNamespace(status_code=200)

        first = threading.Thread(target=lambda: results.append(self.probe.check(slow_requester)))
        second = threading.Thread(target=lambda: results.append(self.probe.check(slow_requester)))
        first.start()
        self.assertTrue(entered.wait(timeout=2))
        second.start()
        release.set()
        first.join(timeout=2)
        second.join(timeout=2)

        self.assertFalse(first.is_alive())
        self.assertFalse(second.is_alive())
        self.assertEqual(call_count, 1)
        self.assertEqual(len(results), 2)
        self.assertIs(results[0], results[1])

    def test_interval_and_timeout_must_be_positive(self):
        with self.assertRaises(ValueError):
            StatusProbe(request_interval_seconds=0)
        with self.assertRaises(ValueError):
            StatusProbe(timeout_seconds=0)


if __name__ == "__main__":
    unittest.main()
