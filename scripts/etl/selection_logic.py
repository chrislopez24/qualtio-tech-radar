from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from etl.ai_filter import (
    FilteredItem,
    StrategicValue,
    is_resource_like_repository,
    is_strong_ring_editorially_eligible,
    is_trial_ring_editorially_eligible,
)
from etl.classifier import ClassificationResult
from etl.candidate_selector import CandidateSelection

logger = logging.getLogger(__name__)


PLACEHOLDER_RING = "trial"
RING_FILL_ORDER = ("adopt", "trial", "assess", "hold")


def _eligible_selected_item(pipeline: Any, tech: Any, classification: ClassificationResult, confidence_floor: float = 0.5) -> Optional[FilteredItem]:
    item = pipeline._build_filtered_item(tech, classification, confidence_floor=confidence_floor)
    if not pipeline._is_editorially_valid_for_selection(item):
        return None
    return item


def _selection_signal_bonus(signals: Any) -> float:
    if not isinstance(signals, dict):
        return 0.0
    source_coverage = float(signals.get("source_coverage", 0.0) or 0.0)
    has_external_adoption = float(signals.get("has_external_adoption", 0.0) or 0.0)
    return (source_coverage * 1.5) + (has_external_adoption * 4.0)


def _selection_ring(_classification: ClassificationResult) -> str:
    return PLACEHOLDER_RING


def _selection_score(item: FilteredItem) -> float:
    return (
        float(getattr(item, "market_score", 0.0)) * float(item.confidence)
        + _selection_signal_bonus(getattr(item, "signals", {}))
    )


def _ring_counts(items: Sequence[FilteredItem]) -> Dict[str, int]:
    counts = {ring: 0 for ring in RING_FILL_ORDER}
    for item in items:
        ring = str(getattr(item, "ring", "")).strip().lower()
        if ring in counts:
            counts[ring] += 1
    return counts


def rebalance_soft_ring_targets(
    pipeline: Any,
    selected: List[FilteredItem],
    reserve_candidates: Sequence[FilteredItem],
    radar_quadrants: Sequence[str],
) -> List[FilteredItem]:
    target_total = max(0, int(getattr(pipeline.config.distribution, "target_total", len(selected)) or 0))
    target_per_ring = max(0, int(getattr(pipeline.config.distribution, "target_per_ring", 0) or 0))
    max_per_ring = max(target_per_ring, int(getattr(pipeline.config.distribution, "max_per_ring", target_per_ring) or 0))
    if target_per_ring <= 0 and max_per_ring <= 0:
        return selected

    min_per_quadrant = max(1, int(getattr(pipeline.config.distribution, "min_per_quadrant", 1) or 1))
    max_per_quadrant = max(min_per_quadrant, int(getattr(pipeline.config.distribution, "max_per_quadrant", target_total or len(selected) or 1) or 1))
    target_min = max(len(radar_quadrants), target_total - 3) if target_total else len(selected)

    selected_ids = {pipeline._normalize_id(item.name) for item in selected}
    reserve = [
        item
        for item in reserve_candidates
        if pipeline._normalize_id(item.name) not in selected_ids
    ]
    reserve.sort(
        key=lambda item: (
            _selection_score(item),
            1 if pipeline._is_editorially_valid_for_selection(item) else 0,
        ),
        reverse=True,
    )

    def quadrant_count(quadrant: str) -> int:
        return sum(1 for item in selected if item.quadrant == quadrant)

    ring_counts = _ring_counts(selected)

    for ring in RING_FILL_ORDER:
        while len(selected) < target_total and ring_counts.get(ring, 0) < target_per_ring:
            candidate_index: Optional[int] = None
            for index, candidate in enumerate(reserve):
                if str(getattr(candidate, "ring", "")).strip().lower() != ring:
                    continue
                if not pipeline._is_editorially_valid_for_selection(candidate):
                    continue
                if quadrant_count(candidate.quadrant) >= max_per_quadrant:
                    continue
                candidate_index = index
                break

            if candidate_index is None:
                break

            candidate = reserve.pop(candidate_index)
            selected.append(candidate)
            ring_counts[ring] = ring_counts.get(ring, 0) + 1

    if max_per_ring > 0:
        for ring in RING_FILL_ORDER:
            while ring_counts.get(ring, 0) > max_per_ring:
                removable_index: Optional[int] = None
                removable_score: Optional[float] = None
                for index in range(len(selected) - 1, -1, -1):
                    candidate = selected[index]
                    if str(getattr(candidate, "ring", "")).strip().lower() != ring:
                        continue
                    if len(selected) - 1 < target_min:
                        break
                    if quadrant_count(candidate.quadrant) <= min_per_quadrant:
                        continue
                    score = _selection_score(candidate)
                    if removable_score is None or score < removable_score:
                        removable_index = index
                        removable_score = score

                if removable_index is None:
                    break

                selected.pop(removable_index)
                ring_counts[ring] = ring_counts.get(ring, 0) - 1

    return selected


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
        effective_classification = classification
        selection_ring = _selection_ring(classification)
        if len(tech.sources) < min_sources:
            logger.debug(
                "Filtering out %s: only %s sources (min: %s)",
                tech.name,
                len(tech.sources),
                min_sources,
            )
            rejected_low_sources += 1
            continue

        if not pipeline._passes_quality_gate(tech, selection_ring):
            logger.debug(
                "Filtering out %s: doesn't pass quality gate for ring %s",
                tech.name,
                selection_ring,
            )
            rejected_quality_gate += 1
            continue

        if is_resource_like_repository(tech.name, classification.description or tech.description):
            logger.debug(
                "Filtering out %s: resource-like repository is not eligible for selection",
                tech.name,
            )
            rejected_quality_gate += 1
            continue

        raw_signals = getattr(tech, "signals", {}) or {}
        if not isinstance(raw_signals, dict):
            raw_signals = {}
        gh_momentum = float(raw_signals.get("gh_momentum", 0.0) or 0.0)
        gh_popularity = float(raw_signals.get("gh_popularity", 0.0) or 0.0)
        hn_heat = float(raw_signals.get("hn_heat", 0.0) or 0.0)
        source_coverage = float(raw_signals.get("source_coverage", 0.0) or 0.0)
        github_only_raw = raw_signals.get("github_only")
        if github_only_raw is None:
            github_only = (gh_momentum > 0.0 or gh_popularity > 0.0) and hn_heat <= 0.0
        else:
            github_only = bool(float(github_only_raw or 0.0))
        has_external_adoption = bool(float(raw_signals.get("has_external_adoption", 0.0) or 0.0))
        if source_coverage > 0.0 and source_coverage <= 1.0 and (gh_momentum > 0.0 or gh_popularity > 0.0) and not has_external_adoption:
            github_only = True
        editorially_plausible = is_trial_ring_editorially_eligible(
            tech.name,
            effective_classification.description or tech.description,
            getattr(tech, "topics", []),
        )
        if (
            github_only
            and not has_external_adoption
            and hn_heat <= 0.0
            and (float(tech.market_score) < 60.0 or not editorially_plausible)
        ):
            logger.debug(
                "Filtering out %s: low-confidence/editorially-weak candidate with GitHub-only evidence",
                tech.name,
            )
            rejected_quality_gate += 1
            continue

        qualified_techs.append((tech, effective_classification))

    logger.info(
        "Phase 5 - %s technologies passed quality gates out of %s classified",
        len(qualified_techs),
        len(classified_pairs),
    )
    qualified_lookup: Dict[str, Tuple[Any, ClassificationResult]] = {
        pipeline._normalize_id(classification.name): (tech, classification)
        for tech, classification in qualified_techs
    }

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
                    "ring": PLACEHOLDER_RING,
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

    for item in sorted(ai_filtered, key=_selection_score, reverse=True):
        item_id = pipeline._normalize_id(item.name)
        if item_id in previous_watchlist_ids:
            continue
        pair = qualified_lookup.get(item_id)
        if pair is not None:
            tech, classification = pair
            hydrated = _eligible_selected_item(pipeline, tech, classification, confidence_floor=0.5)
            if hydrated is None:
                continue
            hydrated.quadrant = item.quadrant
            hydrated.description = item.description
            hydrated.trend = item.trend
            hydrated.strategic_value = item.strategic_value
            hydrated.is_deprecated = bool(getattr(item, "is_deprecated", False))
            hydrated.replacement = getattr(item, "replacement", None)
            ai_flags = list(getattr(item, "suspicion_flags", []) or [])
            existing_flags = list(getattr(hydrated, "suspicion_flags", []) or [])
            merged_flags: List[str] = []
            for flag in existing_flags + ai_flags:
                normalized = str(flag or "").strip()
                if normalized and normalized not in merged_flags:
                    merged_flags.append(normalized)
            hydrated.suspicion_flags = merged_flags
            selected.append(hydrated)
        else:
            selected.append(item)
        selected_ids.add(item_id)

    ranked_candidates = sorted(
        qualified_techs,
        key=lambda pair: (
            1 if pipeline._normalize_id(pair[1].name) in previous_main_ids else 0,
            pair[0].market_score * pair[1].confidence + _selection_signal_bonus(pair[0].signals),
        ),
        reverse=True,
    )
    pipeline._last_selection_candidates = [
        pipeline._build_filtered_item(tech, classification, confidence_floor=0.5)
        for tech, classification in ranked_candidates
    ]

    for quadrant in radar_quadrants:
        while _quadrant_count(quadrant) < min_per_quadrant and len(selected) < target_max:
            added = False
            remaining_needs = {
                needed_quadrant
                for needed_quadrant in radar_quadrants
                if _quadrant_count(needed_quadrant) < min_per_quadrant
            }
            for tech, classification in ranked_candidates:
                item_id = pipeline._normalize_id(classification.name)
                if item_id in selected_ids:
                    continue
                if classification.quadrant != quadrant:
                    continue
                inferred_quadrant = pipeline._infer_quadrant(tech)
                if inferred_quadrant in remaining_needs and inferred_quadrant != quadrant:
                    continue
                candidate_item = _eligible_selected_item(pipeline, tech, classification, confidence_floor=0.5)
                if candidate_item is None:
                    continue
                selected.append(candidate_item)
                selected_ids.add(item_id)
                added = True
                break

            if not added:
                best_fit: Optional[Tuple[Any, ClassificationResult, float]] = None
                for tech, classification in ranked_candidates:
                    item_id = pipeline._normalize_id(classification.name)
                    if item_id in selected_ids:
                        continue
                    inferred_quadrant = pipeline._infer_quadrant(tech)
                    if inferred_quadrant in remaining_needs and inferred_quadrant != quadrant:
                        continue
                    affinity = pipeline._quadrant_affinity(tech, quadrant)
                    if best_fit is None or affinity > best_fit[2]:
                        best_fit = (tech, classification, affinity)

                if best_fit is not None and best_fit[2] > 0:
                    tech, classification, _ = best_fit
                    item_id = pipeline._normalize_id(classification.name)
                    item = _eligible_selected_item(pipeline, tech, classification, confidence_floor=0.5)
                    if item is None:
                        break
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
        fallback_item = _eligible_selected_item(pipeline, tech, classification, confidence_floor=0.5)
        if fallback_item is None:
            continue
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
        candidate_item = _eligible_selected_item(pipeline, tech, classification, confidence_floor=0.5)
        if candidate_item is None:
            continue
        selected.append(candidate_item)
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
            candidate_item = _eligible_selected_item(pipeline, tech, classification, confidence_floor=0.5)
            if candidate_item is None:
                continue
            selected.append(candidate_item)
            selected_ids.add(item_id)

    if len(selected) < target_min:
        for tech, classification in ranked_candidates:
            if len(selected) >= target_min:
                break
            item_id = pipeline._normalize_id(classification.name)
            if item_id in selected_ids:
                continue
            candidate_item = _eligible_selected_item(pipeline, tech, classification, confidence_floor=0.5)
            if candidate_item is None:
                continue
            selected.append(candidate_item)
            selected_ids.add(item_id)

    selected.sort(
        key=lambda item: (
            1 if pipeline._normalize_id(item.name) in previous_main_ids else 0,
            _selection_score(item),
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

    selected_main = set(main_ids or (candidate_selection.core_ids + candidate_selection.borderline_ids))
    previous_watchlist_ids = [
        pipeline._normalize_id(str(entry.get("id", "")))
        for entry in (pipeline.previous_snapshot or {}).get("watchlist", [])
        if isinstance(entry, dict) and entry.get("id")
    ]
    fallback_watch = sorted(
        [tech for tech in technologies if pipeline._normalize_id(tech.name) not in selected_main],
        key=lambda tech: (tech.trend_delta, tech.market_score),
        reverse=True,
    )

    watchlist_ids: List[str] = []
    for watch_id in candidate_selection.watchlist_ids:
        if watch_id and watch_id not in watchlist_ids:
            watchlist_ids.append(watch_id)
    for watch_id in previous_watchlist_ids:
        if watch_id and watch_id not in watchlist_ids:
            watchlist_ids.append(watch_id)
    for tech in fallback_watch:
        watch_id = pipeline._normalize_id(tech.name)
        if watch_id and watch_id not in watchlist_ids:
            watchlist_ids.append(watch_id)

    watchlist: List[FilteredItem] = []
    seen: Set[str] = set()
    for watch_id in watchlist_ids:
        if len(watchlist) >= target_watchlist:
            break
        if watch_id in seen:
            continue
        if watch_id in selected_main:
            continue

        tech = tech_by_id.get(watch_id)
        if tech is None:
            previous_item = previous_watchlist_map.get(watch_id)
            if previous_item is None:
                continue

            name = str(previous_item.get("name") or previous_item.get("id") or watch_id)
            description = str(previous_item.get("description") or f"{name} remains on the watchlist pending fresh market signals.")
            if is_resource_like_repository(name, description):
                continue
            quadrant = str(previous_item.get("quadrant") or "tools")
            confidence = max(0.5, float(previous_item.get("confidence", 0.6)))
            trend = str(previous_item.get("trend") or "stable")

            item = FilteredItem(
                name=name,
                description=description,
                stars=int(previous_item.get("stars", 0) or 0),
                quadrant=quadrant,
                ring=PLACEHOLDER_RING,
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
                    "source_coverage": float(previous_item.get("sourceCoverage", 0.0) or 0.0),
                    "has_external_adoption": float(
                        (previous_item.get("evidenceSummary", {}) or {}).get("hasExternalAdoption", 0.0) or 0.0
                    ),
                    "github_only": float(
                        (previous_item.get("evidenceSummary", {}) or {}).get("githubOnly", 0.0) or 0.0
                    ),
                },
            )
            evidence_records = pipeline._coerce_evidence_records(previous_item.get("evidence"))
            if not evidence_records:
                evidence_records = pipeline._signal_evidence_fallback(name, getattr(item, "signals", {}) or {})
            setattr(item, "evidence", evidence_records)

            if not pipeline._is_editorially_valid_for_selection(item):
                continue

            watchlist.append(item)
            seen.add(watch_id)
            continue

        classification = classification_by_id.get(watch_id)
        if classification is None:
            classification = ClassificationResult(
                name=tech.name,
                quadrant=pipeline._infer_quadrant(tech),
                description=tech.description or f"{tech.name} is being monitored for growth and adoption potential.",
                confidence=max(0.5, float(tech.signals.get("score_confidence", 0.5))),
                trend="up" if tech.trend_delta >= 0 else "stable",
                strategic_value="medium",
            )
        if is_resource_like_repository(tech.name, classification.description or tech.description):
            continue

        item = pipeline._build_filtered_item(tech, classification, confidence_floor=0.5)
        if tech.trend_delta >= 0:
            item.trend = "up"
        if not pipeline._is_editorially_valid_for_selection(item):
            continue

        watchlist.append(item)
        seen.add(watch_id)

    watchlist.sort(
        key=lambda item: float(getattr(item, "market_score", 0.0)) + (5.0 if item.trend == "up" else 0.0),
        reverse=True,
    )
    return watchlist[:target_watchlist]
