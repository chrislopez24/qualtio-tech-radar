def test_market_score_uses_weighted_external_signals():
    from etl.market_scoring import score_technology

    item = {
        "gh_momentum": 80,
        "gh_popularity": 60,
        "hn_heat": 50,
        "google_momentum": 40,
    }
    score = score_technology(item)
    assert round(score, 2) == 59.0
