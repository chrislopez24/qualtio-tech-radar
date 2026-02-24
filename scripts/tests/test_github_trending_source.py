"""Tests for GitHub Trending Source"""

from unittest.mock import Mock, patch
from etl.config import GitHubTrendingSource as GitHubTrendingConfig
from etl.sources.github_trending import GitHubTrendingSource
from github.GithubException import RateLimitExceededException


class MockRepo:
    def __init__(self, data):
        self.name = data["name"]
        self.full_name = data["full_name"]
        self.description = data["description"]
        self.stars = data["stars"]
        self.forks = data["forks"]
        self.language = data.get("language")
        self.topics = data.get("topics", [])
        self.url = data["url"]
        self.created_at = data["created_at"]
        self.updated_at = data["updated_at"]


def test_github_source_returns_normalized_signals():
    """Test that GitHubTrendingSource returns list of TechnologySignal objects"""
    config = GitHubTrendingConfig(
        enabled=True,
        language="python",
        time_range="daily"
    )
    source = GitHubTrendingSource(config=config)
    items = source.fetch()
    assert isinstance(items, list)


def test_github_source_with_mocked_repos():
    """Test source with mocked repository data"""
    mock_repos = [
        MockRepo({
            "name": "fastapi",
            "full_name": "tiangolo/fastapi",
            "description": "FastAPI framework",
            "stars": 75000,
            "forks": 6000,
            "language": "Python",
            "topics": ["api", "web", "framework"],
            "url": "https://github.com/tiangolo/fastapi",
            "created_at": "2018-06-12T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        })
    ]

    with patch("etl.sources.github_trending.GitHubScraper") as mock_scraper_class:
        mock_scraper = Mock()
        mock_scraper.get_trending_repos.return_value = mock_repos
        mock_scraper_class.return_value = mock_scraper

        config = GitHubTrendingConfig(enabled=True, language="python")
        source = GitHubTrendingSource(config=config)
        items = source.fetch()

        assert len(items) == 1
        assert items[0].name == "fastapi"
        assert items[0].source == "github_trending"
        assert items[0].signal_type == "github_stars"
        assert items[0].score > 0


def test_github_source_respects_language_filter():
    """Test that source filters by language"""
    mock_repos = [
        MockRepo({
            "name": "fastapi",
            "full_name": "tiangolo/fastapi",
            "description": "FastAPI framework",
            "stars": 75000,
            "forks": 6000,
            "language": "Python",
            "topics": [],
            "url": "https://github.com/tiangolo/fastapi",
            "created_at": "2018-06-12T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        }),
        MockRepo({
            "name": "rust-web-server",
            "full_name": "user/rust-web-server",
            "description": "Rust web server",
            "stars": 1000,
            "forks": 100,
            "language": "Rust",
            "topics": [],
            "url": "https://github.com/user/rust-web-server",
            "created_at": "2020-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z"
        })
    ]

    with patch("etl.sources.github_trending.GitHubScraper") as mock_scraper_class:
        mock_scraper = Mock()
        mock_scraper.get_trending_repos.return_value = mock_repos
        mock_scraper_class.return_value = mock_scraper

        config = GitHubTrendingConfig(enabled=True, language="rust")
        source = GitHubTrendingSource(config=config)
        items = source.fetch()

        assert len(items) == 1
        assert items[0].name == "rust-web-server"


def test_github_source_disabled():
    """Test that disabled source returns empty list"""
    config = GitHubTrendingConfig(enabled=False)
    source = GitHubTrendingSource(config=config)
    items = source.fetch()
    assert items == []


class TestRateLimiter:
    """Tests for GitHubRateLimiter features"""

    from etl.rate_limiter import GitHubRateLimiter, RateLimitStatus

    def test_ttl_caching(self):
        """Test that rate limit check uses cache and doesn't hit API repeatedly"""
        limiter = self.GitHubRateLimiter(cache_ttl=60)
        
        mock_status = self.RateLimitStatus(
            remaining=100,
            limit=5000,
            reset_timestamp=int(1000000000),
            used=10
        )
        
        with patch.object(limiter, 'get_rate_limit_status', return_value=mock_status) as mock_get:
            with patch.object(limiter, '_is_cache_valid', return_value=True):
                result1 = limiter.get_rate_limit_status()
                result2 = limiter.get_rate_limit_status()
                
                assert result1 == mock_status
                assert result2 == mock_status

    def test_ttl_cache_expiration(self):
        """Test that cache expires after TTL"""
        limiter = self.GitHubRateLimiter(cache_ttl=60)
        
        mock_status = self.RateLimitStatus(
            remaining=100,
            limit=5000,
            reset_timestamp=int(1000000000),
            used=10
        )
        
        with patch.object(limiter, 'get_rate_limit_status', return_value=mock_status) as mock_get:
            with patch('time.time', side_effect=[1000, 1000, 1065]) as mock_time:
                result1 = limiter.get_rate_limit_status()
                result2 = limiter.get_rate_limit_status()
                
                assert mock_get.call_count == 2

    def test_per_minute_throttle(self):
        """Test that throttle prevents excessive requests"""
        limiter = self.GitHubRateLimiter(requests_per_minute=60)
        
        with patch('time.sleep') as mock_sleep:
            limiter.throttle_per_minute()
            limiter.throttle_per_minute()
            
            assert mock_sleep.call_count >= 1

    def test_exponential_backoff_increases_delay(self):
        """Test that backoff increases delay on failures (2^retry_count)"""
        call_count = 0
        expected_delays = [2, 4, 8]  # 2^1, 2^2, 2^3
        
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count <= 3:
                raise RateLimitExceededException(403, "Rate limit exceeded", {})
            return "success"
        
        limiter = self.GitHubRateLimiter(max_retries=3)
        
        with patch('time.sleep') as mock_sleep:
            with patch.object(limiter, 'throttle_per_minute'):
                with patch.object(limiter, 'wait_if_needed'):
                    result = limiter.execute_with_backoff(failing_func)
            
            assert result == "success"
            assert call_count == 4
            
            sleep_calls = mock_sleep.call_args_list
            assert len(sleep_calls) == 3
            
            actual_delays = [call[0][0] for call in sleep_calls]
            assert actual_delays == expected_delays

    def test_exponential_backoff_first_retry_delay(self):
        """Test that first retry uses 2^1 = 2 seconds"""
        call_count = 0
        
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RateLimitExceededException(403, "Rate limit", {})
            return "success"
        
        limiter = self.GitHubRateLimiter(max_retries=3)
        
        with patch('time.sleep') as mock_sleep:
            limiter.execute_with_backoff(failing_func)
            
            first_delay = mock_sleep.call_args_list[0][0][0]
            assert first_delay == 2