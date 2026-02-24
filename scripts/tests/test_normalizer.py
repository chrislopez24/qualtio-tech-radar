"""Tests for the normalizer module"""

import pytest
from etl.models import TechnologySignal
from etl.normalizer import normalize_signals


def test_normalizer_merges_same_technology_from_multiple_sources():
    """Test that signals from multiple sources are merged into one canonical entry"""
    signals = [
        TechnologySignal(
            name="react",
            source="github_trending",
            signal_type="github_stars",
            score=8.5,
            raw_data={"stars": 85000}
        ),
        TechnologySignal(
            name="React",
            source="hackernews",
            signal_type="hn_mentions",
            score=5.0,
            raw_data={"points": 50}
        ),
        TechnologySignal(
            name="react.js",
            source="google_trends",
            signal_type="google_trends",
            score=3.0,
            raw_data={"interest": 30}
        ),
    ]

    merged = normalize_signals(signals)

    react_signals = [t for t in merged if t.name == "react"]
    assert len(react_signals) == 1
    assert react_signals[0].score > 0


def test_normalizer_case_normalization():
    """Test that case differences are normalized"""
    signals = [
        TechnologySignal(name="REACT", source="github_trending", signal_type="github_stars", score=5.0, raw_data={}),
        TechnologySignal(name="react", source="hackernews", signal_type="hn_mentions", score=3.0, raw_data={}),
    ]

    merged = normalize_signals(signals)

    assert len(merged) == 1
    assert merged[0].name == "react"


def test_normalizer_alias_mapping():
    """Test that aliases are mapped to canonical names"""
    signals = [
        TechnologySignal(name="react.js", source="github_trending", signal_type="github_stars", score=5.0, raw_data={}),
        TechnologySignal(name="reactjs", source="google_trends", signal_type="google_trends", score=3.0, raw_data={}),
    ]

    merged = normalize_signals(signals)

    assert len(merged) == 1
    assert merged[0].name == "react"


def test_normalizer_spacing_normalization():
    """Test that spacing differences are normalized"""
    signals = [
        TechnologySignal(name="machine learning", source="github_trending", signal_type="github_stars", score=5.0, raw_data={}),
        TechnologySignal(name="machine-learning", source="google_trends", signal_type="google_trends", score=3.0, raw_data={}),
    ]

    merged = normalize_signals(signals)

    assert len(merged) == 1
    assert merged[0].name == "machine learning"


def test_normalizer_weighted_source_score():
    """Test that weighted scores are calculated based on source"""
    signals = [
        TechnologySignal(
            name="react",
            source="github_trending",
            signal_type="github_stars",
            score=10.0,
            raw_data={}
        ),
        TechnologySignal(
            name="react",
            source="hackernews",
            signal_type="hn_mentions",
            score=10.0,
            raw_data={}
        ),
        TechnologySignal(
            name="react",
            source="google_trends",
            signal_type="google_trends",
            score=10.0,
            raw_data={}
        ),
    ]

    merged = normalize_signals(signals)

    assert len(merged) == 1
    assert merged[0].score > 10.0


def test_normalizer_preserves_different_technologies():
    """Test that different technologies are not merged"""
    signals = [
        TechnologySignal(name="react", source="github_trending", signal_type="github_stars", score=5.0, raw_data={}),
        TechnologySignal(name="vue", source="github_trending", signal_type="github_stars", score=5.0, raw_data={}),
        TechnologySignal(name="angular", source="github_trending", signal_type="github_stars", score=5.0, raw_data={}),
    ]

    merged = normalize_signals(signals)

    assert len(merged) == 3
    names = [t.name for t in merged]
    assert "react" in names
    assert "vue" in names
    assert "angular" in names


def test_normalizer_empty_list():
    """Test that empty list returns empty list"""
    merged = normalize_signals([])
    assert merged == []


def test_normalizer_single_signal():
    """Test that single signal passes through unchanged"""
    signal = TechnologySignal(
        name="react",
        source="github_trending",
        signal_type="github_stars",
        score=5.0,
        raw_data={"stars": 5000}
    )

    merged = normalize_signals([signal])

    assert len(merged) == 1
    assert merged[0].name == "react"
    assert merged[0].score == 5.0