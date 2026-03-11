from __future__ import annotations

from etl.contracts import LaneEditorialInput, MarketEntity
from etl.signals.scoring import market_score


LANE_ORDER = ("languages", "frameworks", "tools", "platforms", "techniques")
KIND_TO_LANE = {
    "language": "languages",
    "framework": "frameworks",
    "tool": "tools",
    "platform": "platforms",
    "technique": "techniques",
}


def pack_lanes(snapshot: list[MarketEntity]) -> dict[str, LaneEditorialInput]:
    packed = {
        lane: LaneEditorialInput(lane=lane, candidates=[])
        for lane in LANE_ORDER
    }

    for entity in sorted(snapshot, key=market_score, reverse=True):
        lane = KIND_TO_LANE[entity.editorial_kind]
        packed[lane].candidates.append(entity)

    for lane, lane_input in packed.items():
        all_names = [candidate.canonical_name for candidate in lane_input.candidates]
        lane_input.nearby_alternatives = {
            candidate.canonical_slug: [name for name in all_names if name != candidate.canonical_name][:3]
            for candidate in lane_input.candidates
        }
        lane_input.prompt_context = [
            f"Lane: {lane}",
            "Compare candidates within the same market lane, not globally.",
            "Prefer coherent editorial spreads over raw popularity ordering.",
        ]

    return packed
