"""Tests for GitHub Trending Source"""

from unittest.mock import Mock, patch
from etl.config import GitHubTrendingSource as GitHubTrendingConfig
from etl.sources.github_trending import GitHubTrendingSource


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