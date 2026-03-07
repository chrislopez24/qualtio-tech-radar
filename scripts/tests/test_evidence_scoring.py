from etl.evidence import EvidenceRecord


def test_score_evidence_rewards_external_adoption_over_github_only_hype():
    from etl.evidence_scoring import score_evidence

    github_only = score_evidence(
        signals={"gh_momentum": 100.0, "gh_popularity": 100.0, "hn_heat": 0.0},
        evidence=[],
        github_stars=200000,
        github_forks=40000,
    )
    corroborated = score_evidence(
        signals={"gh_momentum": 90.0, "gh_popularity": 88.0, "hn_heat": 45.0},
        evidence=[
            EvidenceRecord(
                source="deps_dev",
                metric="reverse_dependents",
                subject_id="npm:react",
                raw_value=800000,
                normalized_value=97.0,
                observed_at="2026-03-07T00:00:00Z",
                freshness_days=1,
            ),
            EvidenceRecord(
                source="stackexchange",
                metric="tag_activity",
                subject_id="reactjs",
                raw_value=240000,
                normalized_value=89.0,
                observed_at="2026-03-07T00:00:00Z",
                freshness_days=1,
            ),
        ],
        github_stars=230000,
        github_forks=47000,
    )

    assert github_only.github_only is True
    assert github_only.has_external_adoption is False
    assert corroborated.has_external_adoption is True
    assert corroborated.source_coverage >= 3
    assert corroborated.adoption > github_only.adoption
    assert corroborated.composite > github_only.composite


def test_score_evidence_uses_osv_to_reduce_risk_subscore():
    from etl.evidence_scoring import score_evidence

    safer = score_evidence(
        signals={"gh_momentum": 70.0, "gh_popularity": 70.0, "hn_heat": 15.0},
        evidence=[],
    )
    riskier = score_evidence(
        signals={"gh_momentum": 70.0, "gh_popularity": 70.0, "hn_heat": 15.0},
        evidence=[
            EvidenceRecord(
                source="osv",
                metric="known_vulnerabilities",
                subject_id="pypi:fastapi@0.110.0",
                raw_value=3,
                normalized_value=60.0,
                observed_at="2026-03-07T00:00:00Z",
                freshness_days=1,
            )
        ],
    )

    assert riskier.risk < safer.risk
    assert riskier.composite < safer.composite
