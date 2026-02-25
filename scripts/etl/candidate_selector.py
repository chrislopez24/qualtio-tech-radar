from dataclasses import dataclass


@dataclass
class CandidateSelection:
    core_ids: list[str]
    watchlist_ids: list[str]
    borderline_ids: list[str]


def select_candidates(items, target_total, watchlist_ratio, borderline_band):
    """
    Partition items into Core, Watchlist, and Borderline buckets.

    - Core: High market_score + high confidence (stable, mature tech)
    - Watchlist: High trend_delta but lower market_score (emerging/growing tech)
    - Borderline: Items near thresholds or with contradictory signals
    """
    core_ids = []
    watchlist_ids = []
    borderline_ids = []

    for item in items:
        item_id = item["id"]
        market_score = item.get("market_score", 0)
        trend_delta = item.get("trend_delta", 0)
        confidence = item.get("confidence", 0.5)

        # Core criteria: high market score + high confidence
        is_core = market_score >= 70 and confidence >= 0.7

        # Watchlist criteria: high trend delta (momentum) + moderate confidence
        is_watchlist = trend_delta >= 10 and confidence >= 0.5 and not is_core

        # Borderline: neither clearly core nor watchlist, or low confidence
        is_borderline = confidence < 0.5 or (not is_core and not is_watchlist)

        if is_core:
            core_ids.append(item_id)
        elif is_watchlist:
            watchlist_ids.append(item_id)
        elif is_borderline:
            borderline_ids.append(item_id)

    return CandidateSelection(
        core_ids=core_ids,
        watchlist_ids=watchlist_ids,
        borderline_ids=borderline_ids,
    )
