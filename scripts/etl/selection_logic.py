from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from etl.ai_filter import FilteredItem, StrategicValue, is_resource_like_repository
from etl.classifier import ClassificationResult
from etl.candidate_selector import CandidateSelection

logger = logging.getLogger(__name__)


def strategic_filter(
    pipeline: Any,
    technologies: List[Any],
    classifications: List[ClassificationResult],
    radar_quadrants: Sequence[str],
) -> List[FilteredItem]:
    """Phase 5: Quality-gated filtering and balanced selection."""
    classification_by_id: Dict[str, ClassificationResult] = {}
    for classification in classifications:
        key = pipeline._normalize_id(classification.name)
        existing = classification_by_id.get(key)
        if existing is None or classification.confidence >= existing.confidence:
            classification_by_id[key] = classification

    classified_pairs: List[Tuple[Any, ClassificationResult]] = []
    for tech in technologies:
        classification = classification_by_id.get(pipeline._normalize_id(tech.name))
        if classification is not None:
            classified_pairs.append((tech, classification))

    qualified_techs: List[Tuple[Any, ClassificationResult]] = []
    min_sources = getattr(pipeline.config.filtering, "min_sources", 1)
    rejected_low_sources = 0
    rejected_quality_gate = 0
    for tech, classification in classified_pairs:
        if len(tech.sources) < min_sources:
            logger.debug(
                "Filtering out %s: only %s sources (min: %s)",
                tech.name,
                len(tech.sources),
                min_sources,
            )
            rejected_low_sources += 1
            continue

        if not pipeline._passes_quality_gate(tech, classification.ring):
            logger.debug(
                "Filtering out %s: doesn't pass quality gate for ring %s",
                tech.name,
                classification.ring,
            )
            rejected_quality_gate += 1
            continue

        if classification.ring in {"adopt", "trial"} and is_resource_like_repository(tech.name, classification.description or tech.description):
            logger.debug(
                "Filtering out %s: resource-like repository is not eligible for strong editorial rings",
                tech.name,
            )
            rejected_quality_gate += 1
            continue

        qualified_techs.append((tech, classification))

    logger.info(
        "Phase 5 - %s technologies passed quality gates out of %s classified",
        len(qualified_techs),
        len(classified_pairs),
    )

    items = []
    for tech, classification in qualified_techs:
        items.append(
            type(
                "TechItem",
                (),
                {
                    "name": classification.name,
                    "description": classification.description,
                    "stars": tech.stars,
                    "quadrant": classification.quadrant,
                    "ring": classification.ring,
                    "confidence": classification.confidence,
                    "trend": classification.trend,
                    "strategic_value": classification.strategic_value,
                    "market_score": tech.market_score,
                    "signals": tech.signals,
                    "moved": tech.moved,
                    "sources": tech.sources,
                },
            )()
        )

    ai_filtered = pipeline.filter.filter(items) or []
    pipeline._last_filter_stats = {
        "classified": len(classified_pairs),
        "qualified": len(qualified_techs),
        "ai_accepted": len(ai_filtered),
        "rejected_low_sources": rejected_low_sources,
        "rejected_quality_gate": rejected_quality_gate,
        "rejected_ai_filter": max(0, len(qualified_techs) - len(ai_filtered)),
    }

    target_max = getattr(pipeline.config.distribution, "target_total", 15)
    target_min = max(len(radar_quadrants), target_max - 3)

    selected: List[FilteredItem] = []
    selected_ids: Set[str] = set()

    def _score(item: FilteredItem) -> float:
        return float(getattr(item, "market_score", 0.0)) * float(item.confidence)

    min_per_quadrant = max(1, int(getattr(pipeline.config.distribution, "min_per_quadrant", 1)))
    max_per_quadrant = max(min_per_quadrant, int(getattr(pipeline.config.distribution, "max_per_quadrant", target_max)))

    def _quadrant_count(quadrant: str) -> int:
        return sum(1 for item in selected if item.quadrant == quadrant)

    previous_main_ids = {
        pipeline._normalize_id(str(entry.get("id", "")))
        for entry in (pipeline.previous_snapshot or {}).get("technologies", [])
        if isinstance(entry, dict) and entry.get("id")
    }
    previous_watchlist_ids = {
        pipeline._normalize_id(str(entry.get("id", "")))
        for entry in (pipeline.previous_snapshot or {}).get("watchlist", [])
        if isinstance(entry, dict) and entry.get("id")
    }

    for item in sorted(ai_filtered, key=_score, reverse=True):
        item_id = pipeline._normalize_id(item.name)
        if item_id in previous_watchlist_ids:
            continue
        selected.append(item)
        selected_ids.add(item_id)

    ranked_candidates = sorted(
        qualified_techs,
        key=lambda pair: (
            1 if pipeline._normalize_id(pair[1].name) in previous_main_ids else 0,
            pair[0].market_score * pair[1].confidence,
        ),
        reverse=True,
    )

    for quadrant in radar_quadrants:
        while _quadrant_count(quadrant) < min_per_quadrant and len(selected) < target_max:
            added = False
            for tech, classification in ranked_candidates:
                item_id = pipeline._normalize_id(classification.name)
                if item_id in selected_ids:
                    continue
                if classification.quadrant != quadrant:
                    continue
                selected.append(pipeline._build_filtered_item(tech, classification, confidence_floor=0.5))
                selected_ids.add(item_id)
                added = True
                break

            if not added:
                best_fit: Optional[Tuple[Any, ClassificationResult, float]] = None
                for tech, classification in ranked_candidates:
                    item_id = pipeline._normalize_id(classification.name)
                    if item_id in selected_ids:
                        continue
                    affinity = pipeline._quadrant_affinity(tech, quadrant)
                    if best_fit is None or affinity > best_fit[2]:
                        best_fit = (tech, classification, affinity)

                if best_fit is not None and best_fit[2] > 0:
                    tech, classification, _ = best_fit
                    item_id = pipeline._normalize_id(classification.name)
                    item = pipeline._build_filtered_item(tech, classification, confidence_floor=0.5)
                    item.quadrant = quadrant
                    selected.append(item)
                    selected_ids.add(item_id)
                    added = True

            if not added:
                break

    if len(selected) < target_min:
        logger.warning("Filter accepted only %s items, applying deterministic backfill.", len(selected))

    for tech, classification in ranked_candidates:
        if len(selected) >= target_min:
            break
        item_id = pipeline._normalize_id(classification.name)
        if item_id in selected_ids:
            continue
        if item_id in previous_watchlist_ids:
            continue
        if _quadrant_count(classification.quadrant) >= max_per_quadrant:
            continue
        fallback_item = pipeline._build_filtered_item(tech, classification, confidence_floor=0.5)
        selected.append(fallback_item)
        selected_ids.add(item_id)

    for tech, classification in ranked_candidates:
        if len(selected) >= target_max:
            break
        item_id = pipeline._normalize_id(classification.name)
        if item_id in selected_ids:
            continue
        if item_id in previous_watchlist_ids:
            continue
        if _quadrant_count(classification.quadrant) >= max_per_quadrant:
            continue
        selected.append(pipeline._build_filtered_item(tech, classification, confidence_floor=0.5))
        selected_ids.add(item_id)

    if len(selected) < target_min:
        for tech, classification in ranked_candidates:
            if len(selected) >= target_min:
                break
            item_id = pipeline._normalize_id(classification.name)
            if item_id in selected_ids:
                continue
            if item_id in previous_watchlist_ids:
                continue
            selected.append(pipeline._build_filtered_item(tech, classification, confidence_floor=0.5))
            selected_ids.add(item_id)

    if len(selected) < target_min:
        for tech, classification in ranked_candidates:
            if len(selected) >= target_min:
                break
            item_id = pipeline._normalize_id(classification.name)
            if item_id in selected_ids:
                continue
            selected.append(pipeline._build_filtered_item(tech, classification, confidence_floor=0.5))
            selected_ids.add(item_id)

    selected.sort(
        key=lambda item: (
            1 if pipeline._normalize_id(item.name) in previous_main_ids else 0,
            _score(item),
        ),
        reverse=True,
    )
    if len(selected) > target_max:
        idx = len(selected) - 1
        while len(selected) > target_max and idx >= 0:
            candidate = selected[idx]
            same_quadrant_count = sum(1 for item in selected if item.quadrant == candidate.quadrant)
            if same_quadrant_count <= min_per_quadrant:
                idx -= 1
                continue
            selected.pop(idx)
            idx -= 1

    return selected[:target_max]


def build_watchlist_items(
    pipeline: Any,
    technologies: List[Any],
    classifications: List[ClassificationResult],
    candidate_selection: CandidateSelection,
    main_ids: Optional[Set[str]] = None,
) -> List[FilteredItem]:
    """Build dedicated watchlist section separate from main radar blips."""
    if not technologies:
        return []

    tech_by_id = {pipeline._normalize_id(tech.name): tech for tech in technologies}
    classification_by_id = {
        pipeline._normalize_id(classification.name): classification for classification in classifications
    }
    previous_watchlist_map = {
        pipeline._normalize_id(str(entry.get("id", ""))): entry
        for entry in (pipeline.previous_snapshot or {}).get("watchlist", [])
        if isinstance(entry, dict) and entry.get("id")
    }

    target_watchlist = max(
        1,
        int(getattr(pipeline.config.distribution, "target_total", 15) * pipeline.config.llm_optimization.watchlist_ratio),
    )

    watchlist_ids = list(candidate_selection.watchlist_ids)
    if not watchlist_ids:
        selected_main = set(main_ids or (candidate_selection.core_ids + candidate_selection.borderline_ids))
        previous_watchlist_ids = [
            pipeline._normalize_id(str(entry.get("id", "")))
            for entry in (pipeline.previous_snapshot or {}).get("watchlist", [])
            if isinstance(entry, dict) and entry.get("id")
        ]

        for watch_id in previous_watchlist_ids:
            if len(watchlist_ids) >= target_watchlist:
                break
            watchlist_ids.append(watch_id)

        fallback_watch = sorted(
            [tech for tech in technologies if pipeline._normalize_id(tech.name) not in selected_main],
            key=lambda tech: (tech.trend_delta, tech.market_score),
            reverse=True,
        )
        for tech in fallback_watch:
            if len(watchlist_ids) >= target_watchlist:
                break
            watch_id = pipeline._normalize_id(tech.name)
            if watch_id in watchlist_ids:
                continue
            watchlist_ids.append(watch_id)

    watchlist: List[FilteredItem] = []
    seen: Set[str] = set()
    for watch_id in watchlist_ids:
        if len(watchlist) >= target_watchlist:
            break
        if watch_id in seen:
            continue

        tech = tech_by_id.get(watch_id)
        if tech is None:
            previous_item = previous_watchlist_map.get(watch_id)
            if previous_item is None:
                continue

            name = str(previous_item.get("name") or previous_item.get("id") or watch_id)
            description = str(previous_item.get("description") or f"{name} remains on the watchlist pending fresh market signals.")
            quadrant = str(previous_item.get("quadrant") or "tools")
            ring = str(previous_item.get("ring") or "assess")
            confidence = max(0.5, float(previous_item.get("confidence", 0.6)))
            trend = str(previous_item.get("trend") or "stable")

            item = FilteredItem(
                name=name,
                description=description,
                stars=int(previous_item.get("stars", 0) or 0),
                quadrant=quadrant,
                ring=ring,
                confidence=confidence,
                trend=trend,
                strategic_value=StrategicValue.MEDIUM,
                is_deprecated=False,
                replacement=None,
            )

            signals = previous_item.get("signals", {}) if isinstance(previous_item.get("signals"), dict) else {}
            setattr(item, "market_score", float(previous_item.get("marketScore", 0.0) or 0.0))
            setattr(
                item,
                "signals",
                {
                    "gh_momentum": float(signals.get("ghMomentum", 0.0) or 0.0),
                    "gh_popularity": float(signals.get("ghPopularity", 0.0) or 0.0),
                    "hn_heat": float(signals.get("hnHeat", 0.0) or 0.0),
                },
            )

            if item.ring == "adopt":
                item.ring = "trial"

            watchlist.append(item)
            seen.add(watch_id)
            continue

        classification = classification_by_id.get(watch_id)
        if classification is None:
            classification = ClassificationResult(
                name=tech.name,
                quadrant=pipeline._infer_quadrant(tech),
                ring="assess",
                description=tech.description or f"{tech.name} is being monitored for growth and adoption potential.",
                confidence=max(0.5, float(tech.signals.get("score_confidence", 0.5))),
                trend="up" if tech.trend_delta >= 0 else "stable",
                strategic_value="medium",
            )

        item = pipeline._build_filtered_item(tech, classification, confidence_floor=0.5)
        if item.ring == "adopt":
            item.ring = "trial"
        if tech.trend_delta >= 0:
            item.trend = "up"

        watchlist.append(item)
        seen.add(watch_id)

    watchlist.sort(
        key=lambda item: float(getattr(item, "market_score", 0.0)) + (5.0 if item.trend == "up" else 0.0),
        reverse=True,
    )
    return watchlist[:target_watchlist]
