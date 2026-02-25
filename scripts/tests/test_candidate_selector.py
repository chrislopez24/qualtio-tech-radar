def test_selector_splits_core_watchlist_and_borderline():
    from etl.candidate_selector import select_candidates

    items = [
        {"id": "react", "market_score": 92, "trend_delta": 3, "confidence": 0.9},
        {"id": "new-framework", "market_score": 58, "trend_delta": 18, "confidence": 0.6},
        {"id": "edge-tool", "market_score": 61, "trend_delta": 1, "confidence": 0.45},
    ]
    out = select_candidates(items, target_total=10, watchlist_ratio=0.3, borderline_band=5.0)
    assert "react" in out.core_ids
    assert "new-framework" in out.watchlist_ids
    assert "edge-tool" in out.borderline_ids
