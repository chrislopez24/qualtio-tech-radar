"""Tests for the temporal analyzer module"""

import pytest
from datetime import datetime, timedelta
from etl.models import TechnologySignal
from etl.temporal_analyzer import TemporalAnalyzer


def test_temporal_analyzer_returns_trend_and_activity_score():
    """Test that temporal analysis returns trend and activity score"""
    signals = [
        TechnologySignal(
            name="react",
            source="github_trending",
            signal_type="github_stars",
            score=8.5,
            raw_data={"stars": 85000, "trending_date": "2024-01-15"}
        ),
        TechnologySignal(
            name="react",
            source="hackernews",
            signal_type="hn_mentions",
            score=5.0,
            raw_data={"points": 50, "trending_date": "2024-01-20"}
        ),
    ]

    analysis = TemporalAnalyzer().analyze(signals)

    assert analysis.trend in {"growing", "stable", "declining", "new"}
    assert analysis.activity_score >= 0


def test_temporal_analyzer_growing_trend():
    """Test detection of growing trend (activity spanning recent days)"""
    now = datetime.now()
    signals = [
        TechnologySignal(
            name="new-tech",
            source="github_trending",
            signal_type="github_stars",
            score=9.0,
            raw_data={"trending_date": (now - timedelta(days=5)).strftime("%Y-%m-%d")}
        ),
        TechnologySignal(
            name="new-tech",
            source="hackernews",
            signal_type="hn_mentions",
            score=8.0,
            raw_data={"trending_date": (now - timedelta(days=15)).strftime("%Y-%m-%d")}
        ),
        TechnologySignal(
            name="new-tech",
            source="github_trending",
            signal_type="github_stars",
            score=7.0,
            raw_data={"trending_date": (now - timedelta(days=25)).strftime("%Y-%m-%d")}
        ),
    ]

    analysis = TemporalAnalyzer().analyze(signals)

    assert analysis.trend == "growing"


def test_temporal_analyzer_declining_trend():
    """Test detection of declining trend (older activity only)"""
    signals = [
        TechnologySignal(
            name="legacy-tech",
            source="github_trending",
            signal_type="github_stars",
            score=3.0,
            raw_data={"trending_date": "2023-01-15"}
        ),
        TechnologySignal(
            name="legacy-tech",
            source="hackernews",
            signal_type="hn_mentions",
            score=2.0,
            raw_data={"trending_date": "2023-02-20"}
        ),
    ]

    analysis = TemporalAnalyzer().analyze(signals)

    assert analysis.trend == "declining"


def test_temporal_analyzer_stable_trend():
    """Test detection of stable trend (mixed recent and older activity)"""
    now = datetime.now()
    signals = [
        TechnologySignal(
            name="stable-tech",
            source="github_trending",
            signal_type="github_stars",
            score=6.0,
            raw_data={"trending_date": (now - timedelta(days=20)).strftime("%Y-%m-%d")}
        ),
        TechnologySignal(
            name="stable-tech",
            source="hackernews",
            signal_type="hn_mentions",
            score=5.0,
            raw_data={"trending_date": (now - timedelta(days=80)).strftime("%Y-%m-%d")}
        ),
    ]

    analysis = TemporalAnalyzer().analyze(signals)

    assert analysis.trend == "stable"


def test_temporal_analyzer_new_technology():
    """Test detection of new technology (very recent activity)"""
    now = datetime.now()
    signals = [
        TechnologySignal(
            name="brand-new",
            source="github_trending",
            signal_type="github_stars",
            score=10.0,
            raw_data={"trending_date": (now - timedelta(days=1)).strftime("%Y-%m-%d")}
        ),
    ]

    analysis = TemporalAnalyzer().analyze(signals)

    assert analysis.trend == "new"


def test_temporal_analyzer_empty_signals():
    """Test that empty signals returns default values"""
    analysis = TemporalAnalyzer().analyze([])

    assert analysis.trend == "stable"
    assert analysis.activity_score == 0.0


def test_temporal_analyzer_domain_breakdown():
    """Test optional domain breakdown"""
    signals = [
        TechnologySignal(
            name="react",
            source="github_trending",
            signal_type="github_stars",
            score=8.0,
            raw_data={"trending_date": "2024-01-15"}
        ),
        TechnologySignal(
            name="react",
            source="hackernews",
            signal_type="hn_mentions",
            score=6.0,
            raw_data={"trending_date": "2024-01-15"}
        ),
    ]

    analysis = TemporalAnalyzer().analyze(signals, include_domain_breakdown=True)

    assert analysis.domain_breakdown is not None
    assert "github_trending" in analysis.domain_breakdown
    assert "hackernews" in analysis.domain_breakdown


def test_temporal_analyzer_buckets():
    """Test that signals are correctly bucketed"""
    now = datetime.now()
    signals = [
        TechnologySignal(
            name="tech1",
            source="github_trending",
            signal_type="github_stars",
            score=8.0,
            raw_data={"trending_date": (now - timedelta(days=5)).strftime("%Y-%m-%d")}
        ),
        TechnologySignal(
            name="tech2",
            source="github_trending",
            signal_type="github_stars",
            score=5.0,
            raw_data={"trending_date": (now - timedelta(days=45)).strftime("%Y-%m-%d")}
        ),
        TechnologySignal(
            name="tech3",
            source="github_trending",
            signal_type="github_stars",
            score=3.0,
            raw_data={"trending_date": (now - timedelta(days=200)).strftime("%Y-%m-%d")}
        ),
    ]

    analysis = TemporalAnalyzer().analyze(signals)

    assert analysis.recent_count == 1
    assert analysis.new_count == 1
    assert analysis.legacy_count == 1
