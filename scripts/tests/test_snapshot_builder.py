from etl.contracts import MarketEntity


def test_snapshot_builder_produces_entities_with_adoption_and_momentum():
    from etl.signals.snapshot_builder import build_market_snapshot

    snapshot = build_market_snapshot(
        [
            MarketEntity(
                canonical_name="React",
                canonical_slug="react",
                editorial_kind="framework",
                topic_family="ui",
                source_evidence=[
                    {"source": "seed", "metric": "curated_presence", "normalized_value": 70},
                    {"source": "github", "metric": "github_stars", "normalized_value": 95},
                ],
            )
        ]
    )

    assert len(snapshot) == 1
    assert snapshot[0].adoption_signals["adoption"] > 0
    assert snapshot[0].momentum_signals["momentum"] > 0
    assert snapshot[0].maturity_signals["maturity"] >= 0
    assert snapshot[0].risk_signals["risk"] >= 0
