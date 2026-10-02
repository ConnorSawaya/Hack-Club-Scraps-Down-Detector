"""Conservative, process-wide status checks for scraps.hackclub.com."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Callable

import requests

SCRAPS_URL = "https://scraps.hackclub.com"
REQUEST_TIMEOUT_SECONDS = 5
MIN_REQUEST_INTERVAL_SECONDS = 60
REQUEST_HEADERS = {
    "User-Agent": (
        "ScrapsDownDetector/1.0 "
        "(+https://github.com/ConnorSawaya/Hack-Club-Scraps-Down-Detector)"
    )
}

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class StatusResult:
    """One status response shared by all sessions in this server process."""

    status_code: int | None
    checked_at: datetime
    error: str | None = None


class StatusProbe:
    """Cache and throttle requests to the fixed Scraps homepage."""

    def __init__(
        self,
        *,
        request_interval_seconds: int = MIN_REQUEST_INTERVAL_SECONDS,
        timeout_seconds: int = REQUEST_TIMEOUT_SECONDS,
        monotonic: Callable[[], float] = time.monotonic,
        wall_clock: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        if request_interval_seconds < 1:
            raise ValueError("request_interval_seconds must be at least 1")
        if timeout_seconds < 1:
            raise ValueError("timeout_seconds must be at least 1")

        self._request_interval_seconds = request_interval_seconds
        self._timeout_seconds = timeout_seconds
        self._monotonic = monotonic
        self._wall_clock = wall_clock
        self._lock = Lock()
        self._cached_result: StatusResult | None = None
        self._next_request_at = 0.0

    def check(self, requester: Callable[..., requests.Response] = requests.get) -> StatusResult:
        """Return the cached result or make one bounded, rate-limited request.

        Failed requests are cached for the same interval, preventing connected
        sessions from retrying the external site in a tight loop.
        """

        with self._lock:
            started_at = self._monotonic()
            if self._cached_result is not None and started_at < self._next_request_at:
                return self._cached_result

            # Set the limit before I/O so concurrent sessions queue behind this
            # check instead of starting additional requests.
            self._next_request_at = started_at + self._request_interval_seconds
            try:
                response = requester(
                    SCRAPS_URL,
                    headers=REQUEST_HEADERS,
                    timeout=self._timeout_seconds,
                    allow_redirects=False,
                )
                result = StatusResult(
                    status_code=response.status_code,
                    checked_at=self._wall_clock(),
                )
            except requests.Timeout:
                result = StatusResult(
                    status_code=None,
                    checked_at=self._wall_clock(),
                    error="timeout",
                )
            except requests.RequestException:
                result = StatusResult(
                    status_code=None,
                    checked_at=self._wall_clock(),
                    error="request",
                )
            except Exception as error:
                logger.error(
                    "Unexpected error while checking Scraps status (%s)",
                    type(error).__name__,
                )
                result = StatusResult(
                    status_code=None,
                    checked_at=self._wall_clock(),
                    error="unexpected",
                )

            self._cached_result = result
            return result


_SCRAPS_STATUS_PROBE = StatusProbe()


def check_scraps_status() -> StatusResult:
    """Get the process-wide cached status for the Scraps homepage."""

    return _SCRAPS_STATUS_PROBE.check()
