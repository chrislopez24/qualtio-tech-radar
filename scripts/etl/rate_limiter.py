"""Reusable rate limiter with caching and exponential backoff"""

import os
import time
import logging
import requests
from dataclasses import dataclass, field
from typing import Callable, Any, Optional
from functools import wraps
from threading import Lock

from github import Github
from github.GithubException import RateLimitExceededException, GithubException

logger = logging.getLogger(__name__)


@dataclass
class RateLimitStatus:
    remaining: int
    limit: int
    reset_timestamp: int
    used: int


class GitHubRateLimiter:
    def __init__(
        self,
        token: Optional[str] = None,
        requests_per_minute: int = 30,
        max_retries: int = 3,
        cache_ttl: int = 60,
    ):
        self.token = token or os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        self.client = Github(self.token) if self.token else None
        self.requests_per_minute = requests_per_minute
        self.max_retries = max_retries
        self.cache_ttl = cache_ttl

        self._rate_limit_cache: Optional[RateLimitStatus] = None
        self._cache_timestamp: float = 0
        self._lock = Lock()
        self._last_request_time: float = 0

    def _is_cache_valid(self) -> bool:
        if self._rate_limit_cache is None:
            return False
        return (time.time() - self._cache_timestamp) < self.cache_ttl

    def get_rate_limit_status(self) -> Optional[RateLimitStatus]:
        if self._is_cache_valid():
            return self._rate_limit_cache

        try:
            if self.client:
                rate_limit = self.client.get_rate_limit()
                core = rate_limit.resources.core
                status = RateLimitStatus(
                    remaining=core.remaining,
                    limit=core.limit,
                    reset_timestamp=core.reset,
                    used=core.used,
                )
            else:
                session = requests.Session()
                headers = {"Accept": "application/vnd.github.v3+json"}
                if self.token:
                    headers["Authorization"] = f"token {self.token}"

                response = session.get(
                    "https://api.github.com/rate_limit", headers=headers
                )
                response.raise_for_status()
                data = response.json()
                core = data["resources"]["core"]
                status = RateLimitStatus(
                    remaining=core["remaining"],
                    limit=core["limit"],
                    reset_timestamp=core["reset"],
                    used=core["used"],
                )

            self._rate_limit_cache = status
            self._cache_timestamp = time.time()
            return status

        except Exception as e:
            logger.warning(f"Could not fetch rate limit status: {e}")
            return None

    def wait_if_needed(self, min_remaining: int = 10) -> None:
        status = self.get_rate_limit_status()
        if status and status.remaining < min_remaining:
            wait_time = max(0, status.reset_timestamp - int(time.time())) + 1
            logger.info(
                f"Rate limit low ({status.remaining} remaining). Waiting {wait_time}s..."
            )
            time.sleep(wait_time)

    def throttle_per_minute(self) -> None:
        with self._lock:
            now = time.time()
            elapsed = now - self._last_request_time
            min_interval = 60.0 / self.requests_per_minute

            if elapsed < min_interval:
                sleep_time = min_interval - elapsed
                time.sleep(sleep_time)

            self._last_request_time = time.time()

    def _handle_retry(self, retry_count: int, error: Exception, error_type: str) -> None:
        if retry_count > self.max_retries:
            raise

        wait_time = 2**retry_count
        logger.warning(
            f"{error_type}. Retry {retry_count}/{self.max_retries} "
            f"in {wait_time}s..."
        )
        time.sleep(wait_time)

    def execute_with_backoff(
        self, func: Callable[[], Any], *args, **kwargs
    ) -> Any:
        retry_count = 0
        last_exception = None

        while retry_count <= self.max_retries:
            try:
                self.throttle_per_minute()
                self.wait_if_needed()

                result = func(*args, **kwargs)
                return result

            except RateLimitExceededException as e:
                retry_count += 1
                last_exception = e
                self._handle_retry(retry_count, e, "Rate limit exceeded")

            except GithubException as e:
                retry_count += 1
                last_exception = e
                self._handle_retry(retry_count, e, "GitHub API error")

            except Exception as e:
                if "403" in str(e) or "Rate Limit Exceeded" in str(e):
                    retry_count += 1
                    last_exception = e
                    self._handle_retry(retry_count, e, "HTTP 403 rate limit")
                else:
                    raise

        raise last_exception or Exception("Max retries exceeded")


def with_rate_limiter(rate_limiter: GitHubRateLimiter):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            return rate_limiter.execute_with_backoff(func, *args, **kwargs)

        return wrapper

    return decorator