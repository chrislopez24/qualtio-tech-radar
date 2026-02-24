import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from etl.config import HackerNewsSource
from etl.sources.hackernews import HackerNewsItem, HackerNewsSource as HNSource


@pytest.fixture
def config():
    return HackerNewsSource(
        enabled=True,
        min_points=10,
        days_back=7
    )


@pytest.fixture
def mock_hn_items():
    now = datetime.now()
    return [
        HackerNewsItem(
            id=1,
            title="Show HN: I built a React 19 app with new features",
            url="https://example.com/react-app",
            points=50,
            author="user1",
            created_at=int((now - timedelta(hours=5)).timestamp()),
            comment_count=10
        ),
        HackerNewsItem(
            id=2,
            title="Show HN: Python fastapi tutorial",
            url="https://example.com/fastapi",
            points=25,
            author="user2",
            created_at=int((now - timedelta(days=2)).timestamp()),
            comment_count=5
        ),
        HackerNewsItem(
            id=3,
            title="Show HN: My new blog about cooking",
            url="https://example.com/cooking",
            points=5,
            author="user3",
            created_at=int((now - timedelta(hours=2)).timestamp()),
            comment_count=2
        ),
        HackerNewsItem(
            id=4,
            title="Show HN: Docker Kubernetes guide",
            url="https://example.com/k8s",
            points=100,
            author="user4",
            created_at=int((now - timedelta(days=10)).timestamp()),
            comment_count=20
        ),
    ]


def test_hn_source_applies_points_filter(config, mock_hn_items):
    """Test that the source filters items by minimum points"""
    with patch('etl.sources.hackernews.HackerNewsAPI') as MockAPI:
        mock_api = MockAPI.return_value
        mock_api.fetch_stories.return_value = mock_hn_items
        
        source = HNSource(config=config)
        items = list(source.fetch())
        
        assert all(i.points >= config.min_points for i in items)


def test_hn_source_applies_days_back_filter(config, mock_hn_items):
    """Test that the source filters items by days_back"""
    with patch('etl.sources.hackernews.HackerNewsAPI') as MockAPI:
        mock_api = MockAPI.return_value
        mock_api.fetch_stories.return_value = mock_hn_items
        
        source = HNSource(config=config)
        items = list(source.fetch())
        
        cutoff = datetime.now() - timedelta(days=config.days_back)
        cutoff_timestamp = cutoff.timestamp()
        
        for item in items:
            item_time = item.created_at if isinstance(item.created_at, (int, float)) else 0
            assert item_time >= cutoff_timestamp


def test_hn_source_scans_max_stories(config):
    """Test that the source has a max stories scan cap"""
    with patch('etl.sources.hackernews.HackerNewsAPI') as MockAPI:
        mock_api = MockAPI.return_value
        mock_api.fetch_stories.return_value = []
        
        source = HNSource(config=config)
        
        assert hasattr(source, 'max_stories_scan')
        assert source.max_stories_scan == 500


def test_hn_source_tech_relevance_scoring(config, mock_hn_items):
    """Test that the source applies tech relevance scoring"""
    with patch('etl.sources.hackernews.HackerNewsAPI') as MockAPI:
        mock_api = MockAPI.return_value
        mock_api.fetch_stories.return_value = mock_hn_items
        
        source = HNSource(config=config)
        items = list(source.fetch())
        
        for item in items:
            assert item.tech_score > 0, f"Item {item.id} should have tech_score > 0"


def test_hn_source_filters_non_tech(config):
    """Test that non-tech items are filtered out"""
    non_tech_items = [
        HackerNewsItem(
            id=1,
            title="Show HN: My new recipe for pasta",
            url="https://example.com/pasta",
            points=50,
            author="chef1",
            created_at=int(datetime.now().timestamp()),
            comment_count=10
        ),
    ]
    
    with patch('etl.sources.hackernews.HackerNewsAPI') as MockAPI:
        mock_api = MockAPI.return_value
        mock_api.fetch_stories.return_value = non_tech_items
        
        source = HNSource(config=config)
        items = list(source.fetch())
        
        assert len(items) == 0