from etl.contracts import MarketEntity


def test_lane_packer_groups_snapshot_entities_by_lane():
    from etl.lanes.packer import pack_lanes

    packed = pack_lanes(
        [
            MarketEntity(
                canonical_name="React",
                canonical_slug="react",
                editorial_kind="framework",
                topic_family="ui",
            )
        ]
    )

    assert set(packed.keys()) == {"languages", "frameworks", "tools", "platforms", "techniques"}
    assert packed["frameworks"].candidates[0].canonical_slug == "react"
