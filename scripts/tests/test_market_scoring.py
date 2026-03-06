def test_market_score_uses_weighted_external_signals():
    from etl.market_scoring import score_technology

    item = {
        "gh_momentum": 80,
        "gh_popularity": 60,
        "hn_heat": 50,
    }
    score = score_technology(item)
    assert score > 70.5


def test_market_score_penalizes_flat_github_only_saturation():
    from etl.market_scoring import score_technology

    github_only = score_technology(
        {
            "gh_momentum": 100,
            "gh_popularity": 100,
            "hn_heat": 0,
        }
    )
    multi_source = score_technology(
        {
            "gh_momentum": 100,
            "gh_popularity": 100,
            "hn_heat": 40,
        }
    )

    assert github_only < 85.0
    assert multi_source > github_only


def test_market_score_keeps_hn_only_buzz_contained():
    from etl.market_scoring import score_technology

    hn_only = score_technology(
        {
            "gh_momentum": 0,
            "gh_popularity": 0,
            "hn_heat": 100,
        }
    )

    assert hn_only < 12.0
