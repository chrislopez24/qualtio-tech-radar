def test_market_snapshot_entity_contract_is_explicit():
    from etl.contracts import MarketEntity

    entity = MarketEntity(
        canonical_name="React",
        canonical_slug="react",
        editorial_kind="framework",
        topic_family="ui",
    )

    assert entity.canonical_slug == "react"
    assert entity.aliases == []
    assert entity.implementation_languages == []


def test_editorial_contracts_can_be_composed():
    from etl.contracts import (
        EditorialDecisionBundle,
        LaneEditorialDecision,
        LaneEditorialInput,
        MarketEntity,
    )

    entity = MarketEntity(
        canonical_name="React",
        canonical_slug="react",
        editorial_kind="framework",
        topic_family="ui",
    )
    lane_input = LaneEditorialInput(lane="frameworks", candidates=[entity])
    decision = LaneEditorialDecision(lane="frameworks", included=[], excluded=[])
    bundle = EditorialDecisionBundle(decisions=[decision])

    assert lane_input.lane == "frameworks"
    assert bundle.decisions[0].lane == "frameworks"
