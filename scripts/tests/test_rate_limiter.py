"""Tests for GitHub rate limiter configuration."""

import warnings

from etl.rate_limiter import GitHubRateLimiter


def test_github_rate_limiter_token_client_avoids_deprecated_auth_api():
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        limiter = GitHubRateLimiter(token="test-token")

    assert limiter.client is not None
