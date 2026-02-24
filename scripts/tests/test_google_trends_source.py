"""Tests for Google Trends Source"""

from unittest.mock import Mock, patch
from etl.config import GoogleTrendsSource as GoogleTrendsConfig
from etl.sources.google_trends import GoogleTrendsSource


def test_google_trends_source_returns_topics():
    """Test that GoogleTrendsSource returns list of TechnologySignal objects"""
    config = GoogleTrendsConfig(
        enabled=True,
        seed_topics=["python", "javascript"]
    )
    source = GoogleTrendsSource(config=config)
    items = source.fetch()
    assert isinstance(items, list)


def test_google_trends_source_with_mocked_data():
    """Test source with mocked trending data"""
    mock_related = [
        {"query": "python tutorial", "value": 100},
        {"query": "javascript framework", "value": 90},
        {"query": "react js", "value": 85},
    ]

    with patch("etl.sources.google_trends.TrendReq") as mock_trend_req:
        mock_trend = Mock()
        mock_trend.related_queries.return_value = {"python": mock_related}
        mock_trend_req.return_value = mock_trend

        config = GoogleTrendsConfig(
            enabled=True,
            seed_topics=["python"]
        )
        source = GoogleTrendsSource(config=config)
        items = source.fetch()

        assert len(items) >= 1
        assert items[0].source == "google_trends"
        assert items[0].signal_type == "trending_search"


def test_google_trends_source_disabled():
    """Test that disabled source returns empty list"""
    config = GoogleTrendsConfig(enabled=False)
    source = GoogleTrendsSource(config=config)
    items = source.fetch()
    assert items == []


def test_google_trends_source_empty_topics():
    """Test that empty seed topics returns empty list"""
    config = GoogleTrendsConfig(enabled=True, seed_topics=[])
    source = GoogleTrendsSource(config=config)
    items = source.fetch()
    assert items == []