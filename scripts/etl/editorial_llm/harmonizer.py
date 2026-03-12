from __future__ import annotations

import math
from datetime import date, timedelta

from etl.contracts import EditorialDecisionBundle, EditorialBlip


RING_STRENGTH = {"adopt": 4, "trial": 3, "assess": 2, "hold": 1}


def harmonize_decisions(bundle: EditorialDecisionBundle, target_total: int = 40) -> dict:
    selected: dict[str, EditorialBlip] = {}
    lane_selected: dict[str, dict[str, EditorialBlip]] = {}
    remaining_exclusions: dict[str, list] = {}
    watchlist: list[dict] = []
    pipeline_meta = {"collected": 0, "qualified": 0, "output": 0, "watchlist": 0}
    lane_target = _lane_target(target_total, len(bundle.decisions))

    for decision in bundle.decisions:
        pipeline_meta["qualified"] += len(decision.included)
        lane_bucket: dict[str, EditorialBlip] = {}
        for blip in decision.included:
            key = blip.canonicalId or blip.id
            current = selected.get(key)
            if current is None or _prefer_candidate(blip, current):
                selected[key] = blip
            lane_bucket[key] = selected[key]
        lane_selected[decision.lane] = lane_bucket
        remaining_exclusions[decision.lane] = sorted(
            decision.excluded,
            key=lambda item: item.marketScore,
            reverse=True,
        )

    for lane, lane_bucket in lane_selected.items():
        while len(lane_bucket) < lane_target and remaining_exclusions[lane]:
            excluded = remaining_exclusions[lane].pop(0)
            backfilled = _promote_exclusion_to_blip(excluded)
            key = backfilled.canonicalId or backfilled.id
            lane_bucket[key] = backfilled
            selected[key] = backfilled

    for lane in lane_selected:
        for excluded in remaining_exclusions[lane][:2]:
            watchlist.append(_watchlist_entry(excluded))

    blips = sorted(selected.values(), key=lambda item: ((item.marketScore or 0.0), item.confidence), reverse=True)[:target_total]
    pipeline_meta["output"] = len(blips)
    pipeline_meta["watchlist"] = len(watchlist)

    return {
        "blips": [blip.model_dump(mode="json") for blip in blips],
        "watchlist": watchlist[:8],
        "meta": {"pipeline": pipeline_meta},
    }


def _prefer_candidate(left: EditorialBlip, right: EditorialBlip) -> bool:
    left_score = left.marketScore or 0.0
    right_score = right.marketScore or 0.0
    if left_score != right_score:
        return left_score > right_score
    if left.confidence != right.confidence:
        return left.confidence > right.confidence
    return RING_STRENGTH[left.ring] > RING_STRENGTH[right.ring]


def _lane_target(target_total: int, lane_count: int) -> int:
    return max(1, math.ceil(target_total / max(1, lane_count)))


def _promote_exclusion_to_blip(excluded) -> EditorialBlip:
    score = excluded.marketScore or 0.0
    return EditorialBlip(
        id=excluded.id,
        name=excluded.name,
        quadrant=excluded.lane,
        ring="assess" if score >= 60 else "hold",
        description=excluded.reason,
        trend="new",
        confidence=0.6 if score >= 60 else 0.5,
        updatedAt=date.today().isoformat(),
        marketScore=score,
        whyThisRing="Promoted during harmonization to preserve lane coverage in the published radar.",
        whyNow="Relevant enough to include once lane balance and overall radar breadth were considered.",
        entityType=excluded.lane[:-1] if excluded.lane.endswith("s") else excluded.lane,
        canonicalId=excluded.id,
    )


def _watchlist_entry(excluded) -> dict:
    return {
        "id": excluded.id,
        "name": excluded.name,
        "quadrant": "tools" if excluded.lane == "frameworks" else excluded.lane,
        "ring": "assess",
        "description": excluded.reason,
        "trend": "new",
        "confidence": 0.55,
        "updatedAt": date.today().isoformat(),
        "marketScore": excluded.marketScore,
        "whyThisRing": "Watchlist because it is relevant but did not make the lane cut this cycle.",
        "entityType": excluded.lane[:-1] if excluded.lane.endswith("s") else excluded.lane,
        "canonicalId": excluded.id,
        "owner": "Radar editorial review",
        "nextStep": "Re-check signal breadth and team relevance next quarter.",
        "nextReviewAt": (date.today() + timedelta(days=90)).isoformat(),
    }
