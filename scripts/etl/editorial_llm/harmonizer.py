from __future__ import annotations

from datetime import date, timedelta

from etl.contracts import EditorialDecisionBundle, EditorialBlip


RING_STRENGTH = {"adopt": 4, "trial": 3, "assess": 2, "hold": 1}


def harmonize_decisions(bundle: EditorialDecisionBundle, target_total: int = 40) -> dict:
    selected: dict[str, EditorialBlip] = {}
    watchlist: list[dict] = []
    pipeline_meta = {"collected": 0, "qualified": 0, "output": 0, "watchlist": 0}

    for decision in bundle.decisions:
        pipeline_meta["qualified"] += len(decision.included)
        for blip in decision.included:
            key = blip.canonicalId or blip.id
            current = selected.get(key)
            if current is None or _prefer_candidate(blip, current):
                selected[key] = blip

        for excluded in decision.excluded[:2]:
            watchlist.append(
                {
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
            )

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
