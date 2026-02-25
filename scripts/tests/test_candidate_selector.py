import pytest
from etl.candidate_selector import select_candidates, CandidateSelection


def test_selector_splits_core_watchlist_and_borderline():
    items = [
        {"id": "react", "market_score": 92, "trend_delta": 3, "confidence": 0.9},
        {"id": "new-framework", "market_score": 58, "trend_delta": 18, "confidence": 0.6},
        {"id": "edge-tool", "market_score": 61, "trend_delta": 1, "confidence": 0.45},
    ]
    out = select_candidates(items, target_total=10, watchlist_ratio=0.3, borderline_band=5.0)
    assert "react" in out.core_ids
    assert "new-framework" in out.watchlist_ids
    assert "edge-tool" in out.borderline_ids


def test_empty_items_list_returns_empty_selection():
    """Test that empty items list returns empty selection (Issue #4)"""
    out = select_candidates([], target_total=10, watchlist_ratio=0.3, borderline_band=5.0)
    assert out.core_ids == []
    assert out.watchlist_ids == []
    assert out.borderline_ids == []


def test_boundary_value_market_score_70():
    """Test boundary value: market_score exactly at core threshold of 70 (Issue #4)"""
    items = [
        {"id": "exact-core-threshold", "market_score": 70, "trend_delta": 3, "confidence": 0.7},
        {"id": "just-below-core", "market_score": 69, "trend_delta": 3, "confidence": 0.7},
    ]
    out = select_candidates(items, target_total=10, watchlist_ratio=0.3, borderline_band=5.0)
    assert "exact-core-threshold" in out.core_ids
    # market_score=69 should be borderline due to proximity to threshold
    assert "just-below-core" in out.borderline_ids


def test_boundary_value_confidence_07():
    """Test boundary value: confidence exactly at threshold of 0.7 (Issue #4)"""
    items = [
        {"id": "exact-confidence", "market_score": 75, "trend_delta": 3, "confidence": 0.7},
        {"id": "just-below-confidence", "market_score": 75, "trend_delta": 3, "confidence": 0.69},
    ]
    out = select_candidates(items, target_total=10, watchlist_ratio=0.3, borderline_band=5.0)
    assert "exact-confidence" in out.core_ids
    # confidence=0.69 should be borderline due to proximity
    assert "just-below-confidence" in out.borderline_ids


def test_size_limiting_logic():
    """Test that size limiting logic works correctly (Issue #4)"""
    items = [
        {"id": f"core-{i}", "market_score": 90 - i, "trend_delta": 3, "confidence": 0.9}
        for i in range(10)
    ]
    out = select_candidates(items, target_total=5, watchlist_ratio=0.2, borderline_band=5.0)
    # Initial bucket sizing keeps core at 3, then selector backfills to target_total.
    assert len(out.core_ids) == 3
    assert len(out.watchlist_ids) <= 1
    total_selected = len(set(out.core_ids + out.watchlist_ids + out.borderline_ids))
    assert total_selected == 5


def test_missing_required_fields_raises_error():
    """Test that missing required fields raises ValueError (Issue #2)"""
    items = [
        {"id": "incomplete", "market_score": 80},  # missing trend_delta and confidence
    ]
    with pytest.raises(ValueError, match="missing required fields"):
        select_candidates(items, target_total=10, watchlist_ratio=0.3, borderline_band=5.0)


def test_borderline_band_affects_classification():
    """Test that borderline_band proximity affects classification (Issue #1)"""
    # Test that items near core threshold are borderline due to proximity
    # market_score=68 is within borderline_band=5 of threshold=70
    items = [
        {"id": "near-core-threshold", "market_score": 68, "trend_delta": 3, "confidence": 0.75},
    ]
    out = select_candidates(items, target_total=10, watchlist_ratio=0.3, borderline_band=5.0)
    assert "near-core-threshold" in out.borderline_ids

    # Test that items near watchlist threshold are borderline
    # trend_delta=8 is within borderline_band=3 of watchlist_threshold=10
    items2 = [
        {"id": "near-watchlist", "market_score": 50, "trend_delta": 8, "confidence": 0.75},
    ]
    out = select_candidates(items2, target_total=10, watchlist_ratio=0.3, borderline_band=3.0)
    assert "near-watchlist" in out.borderline_ids

    # Test that confidence proximity also triggers borderline
    # confidence=0.68 is within borderline_band=0.03 (as percentage) of core_confidence_threshold=0.70
    items3 = [
        {"id": "near-confidence", "market_score": 65, "trend_delta": 3, "confidence": 0.68},
    ]
    out = select_candidates(items3, target_total=10, watchlist_ratio=0.3, borderline_band=3.0)
    assert "near-confidence" in out.borderline_ids


def test_watchlist_high_trend_delta():
    """Test watchlist classification with high trend_delta"""
    items = [
        {"id": "trending-tech", "market_score": 50, "trend_delta": 15, "confidence": 0.6},
    ]
    out = select_candidates(items, target_total=10, watchlist_ratio=0.3, borderline_band=5.0)
    assert "trending-tech" in out.watchlist_ids


def test_low_confidence_goes_to_borderline():
    """Test that low confidence items go to borderline"""
    items = [
        {"id": "low-confidence", "market_score": 80, "trend_delta": 3, "confidence": 0.3},
    ]
    out = select_candidates(items, target_total=10, watchlist_ratio=0.3, borderline_band=5.0)
    assert "low-confidence" in out.borderline_ids


def test_items_sorted_by_market_score():
    """Test that items are sorted by market_score in descending order"""
    items = [
        {"id": "low-score", "market_score": 70, "trend_delta": 3, "confidence": 0.9},
        {"id": "high-score", "market_score": 95, "trend_delta": 3, "confidence": 0.9},
        {"id": "medium-score", "market_score": 82, "trend_delta": 3, "confidence": 0.9},
    ]
    out = select_candidates(items, target_total=10, watchlist_ratio=0.3, borderline_band=5.0)
    assert out.core_ids == ["high-score", "medium-score", "low-score"]


def test_selector_backfills_when_buckets_are_insufficient():
    """Selector should backfill up to target_total when core/watchlist are small."""
    items = [
        {"id": "core-1", "market_score": 95, "trend_delta": 2, "confidence": 0.95},
        {"id": "core-2", "market_score": 90, "trend_delta": 1, "confidence": 0.9},
    ] + [
        {"id": f"border-{i}", "market_score": 55 - i, "trend_delta": 0, "confidence": 0.55}
        for i in range(8)
    ]

    out = select_candidates(items, target_total=8, watchlist_ratio=0.25, borderline_band=5.0)
    total_selected = len(set(out.core_ids + out.watchlist_ids + out.borderline_ids))
    assert total_selected == 8


def test_selector_promotes_borderline_to_core_when_core_empty():
    items = [
        {"id": "top-1", "market_score": 98, "trend_delta": 2, "confidence": 0.55},
        {"id": "top-2", "market_score": 92, "trend_delta": 1, "confidence": 0.56},
        {"id": "top-3", "market_score": 88, "trend_delta": 0, "confidence": 0.57},
        {"id": "other-1", "market_score": 60, "trend_delta": 0, "confidence": 0.52},
        {"id": "other-2", "market_score": 58, "trend_delta": 0, "confidence": 0.51},
        {"id": "other-3", "market_score": 55, "trend_delta": 0, "confidence": 0.5},
    ]

    out = select_candidates(items, target_total=6, watchlist_ratio=0.2, borderline_band=5.0)

    assert out.core_ids == ["top-1", "top-2"]
    assert "top-3" in out.borderline_ids
