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


def test_market_score_keeps_github_only_reference_repo_out_of_adopt_band():
    from etl.market_scoring import score_technology

    github_only_reference = score_technology(
        {
            "gh_momentum": 100,
            "gh_popularity": 93.8,
            "hn_heat": 0,
        },
        source_count=1,
        github_stars=92000,
        github_forks=28000,
    )
    multi_source_mainstream = score_technology(
        {
            "gh_momentum": 95,
            "gh_popularity": 95,
            "hn_heat": 70,
        },
        source_count=2,
        github_stars=230000,
        github_forks=47000,
    )

    assert github_only_reference < 75.0
    assert multi_source_mainstream > github_only_reference
