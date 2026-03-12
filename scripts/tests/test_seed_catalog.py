from collections import Counter


def test_seed_catalog_supports_broad_lane_snapshot():
    from etl.canonical.seeds import get_seed_catalog

    seeds = get_seed_catalog()
    counts = Counter(seed["editorial_kind"] for seed in seeds)

    assert len(seeds) >= 85
    assert counts["language"] >= 17
    assert counts["framework"] >= 17
    assert counts["tool"] >= 17
    assert counts["platform"] >= 17
    assert counts["technique"] >= 17
