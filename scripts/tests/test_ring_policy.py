def test_adopt_requires_non_github_adoption_evidence():
    from etl.ring_policy import decide_ring

    ring = decide_ring(
        {"adoption": 42.0, "mindshare": 90.0, "health": 84.0, "risk": 90.0, "composite": 84.0},
        source_coverage=1,
        has_external_adoption=False,
        github_only=True,
    )

    assert ring != "adopt"


def test_trial_requires_external_corroboration_or_editorial_exception():
    from etl.ring_policy import decide_ring

    without_corroboration = decide_ring(
        {"adoption": 35.0, "mindshare": 78.0, "health": 74.0, "risk": 82.0, "composite": 68.0},
        source_coverage=1,
        has_external_adoption=False,
        github_only=True,
    )
    editorial_exception = decide_ring(
        {"adoption": 35.0, "mindshare": 78.0, "health": 74.0, "risk": 82.0, "composite": 68.0},
        source_coverage=1,
        has_external_adoption=False,
        github_only=True,
        editorial_exception=True,
    )

    assert without_corroboration == "assess"
    assert editorial_exception == "trial"
