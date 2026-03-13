from etl.contracts import EditorialDecisionBundle


def test_runner_builds_named_pipeline_result():
    from etl.runner import build_pipeline_result

    result = build_pipeline_result(
        raw_records=[],
        snapshot=[],
        lane_packs={},
        decisions=EditorialDecisionBundle(decisions=[]),
        harmonized={"blips": [], "watchlist": [], "meta": {}},
        public_preview={"technologies": []},
    )

    assert set(result.keys()) == {
        "raw_records",
        "snapshot",
        "lane_packs",
        "decisions",
        "harmonized",
        "public_preview",
    }


def test_runner_uses_ceiling_lane_budget_for_large_targets():
    from etl.runner import lane_budget

    assert lane_budget(target_total=75, lane_count=5) == 15


def test_main_only_exposes_discovery_sources_via_cli():
    from main import SUPPORTED_SOURCE_NAMES

    assert SUPPORTED_SOURCE_NAMES == {"seed_catalog", "github_trending", "hackernews"}
