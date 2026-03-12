from etl.contracts import EditorialBlip, EditorialDecisionBundle, EditorialExclusion, LaneEditorialDecision


def _blip(lane: str, name: str, score: float) -> EditorialBlip:
    return EditorialBlip(
        id=name.lower().replace(" ", "-"),
        name=name,
        quadrant=lane,
        ring="trial",
        description=f"{name} in {lane}",
        trend="stable",
        confidence=0.8,
        updatedAt="2026-03-12T00:00:00+00:00",
        marketScore=score,
        canonicalId=name.lower().replace(" ", "-"),
    )


def _excluded(lane: str, name: str, score: float) -> EditorialExclusion:
    return EditorialExclusion(
        id=name.lower().replace(" ", "-"),
        name=name,
        reason=f"{name} was below the initial lane cut.",
        lane=lane,
        marketScore=score,
    )


def test_harmonizer_backfills_underfilled_lanes_from_exclusions():
    from etl.editorial_llm.harmonizer import harmonize_decisions

    lanes = ["languages", "frameworks", "tools", "platforms", "techniques"]
    decisions = []
    for lane_index, lane in enumerate(lanes):
        included = [
            _blip(lane, f"{lane}-included-{index}", 90 - index - lane_index)
            for index in range(10)
        ]
        excluded = [
            _excluded(lane, f"{lane}-excluded-{index}", 70 - index - lane_index)
            for index in range(6)
        ]
        decisions.append(LaneEditorialDecision(lane=lane, included=included, excluded=excluded))

    payload = harmonize_decisions(EditorialDecisionBundle(decisions=decisions), target_total=80)
    names = {item["name"] for item in payload["blips"]}

    assert len(payload["blips"]) == 80
    assert "languages-excluded-0" in names
    assert "frameworks-excluded-0" in names
    assert "tools-excluded-0" in names


def test_harmonizer_prefers_lane_balance_before_global_cut():
    from etl.editorial_llm.harmonizer import harmonize_decisions

    bundle = EditorialDecisionBundle(
        decisions=[
            LaneEditorialDecision(
                lane="languages",
                included=[_blip("languages", f"language-{index}", 95 - index) for index in range(6)],
                excluded=[_excluded("languages", f"language-extra-{index}", 70 - index) for index in range(9)],
            ),
            LaneEditorialDecision(
                lane="frameworks",
                included=[_blip("frameworks", f"framework-{index}", 92 - index) for index in range(16)],
                excluded=[],
            ),
            LaneEditorialDecision(
                lane="tools",
                included=[_blip("tools", f"tool-{index}", 91 - index) for index in range(16)],
                excluded=[],
            ),
            LaneEditorialDecision(
                lane="platforms",
                included=[_blip("platforms", f"platform-{index}", 90 - index) for index in range(16)],
                excluded=[],
            ),
            LaneEditorialDecision(
                lane="techniques",
                included=[_blip("techniques", f"technique-{index}", 89 - index) for index in range(16)],
                excluded=[],
            ),
        ]
    )

    payload = harmonize_decisions(bundle, target_total=80)
    names = {item["name"] for item in payload["blips"]}

    assert len(payload["blips"]) == 79
    assert "language-extra-0" in names
    assert "language-extra-8" in names
