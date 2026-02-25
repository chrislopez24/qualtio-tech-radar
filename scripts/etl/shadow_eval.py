"""Shadow quality evaluator for comparing baseline and optimized ETL outputs

This module provides quality metrics to validate that the optimized (selective LLM)
pipeline produces similar results to the baseline (full LLM) pipeline.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Set

logger = logging.getLogger(__name__)


def _extract_llm_calls(payload: Dict[str, Any], *, assume_full_llm_when_missing: bool = False) -> int:
    classified_count: int = 0

    metadata = payload.get("metadata", {}) or {}
    metadata_calls: int | None = None
    if isinstance(metadata, dict):
        value = metadata.get("llm_calls")
        if value is not None:
            try:
                metadata_calls = max(0, int(value))
            except Exception:
                pass

    meta = payload.get("meta", {}) or {}
    pipeline = meta.get("pipeline", {}) if isinstance(meta, dict) else {}
    pipeline_calls: int | None = None
    if isinstance(pipeline, dict):
        classified = pipeline.get("classified")
        if classified is not None:
            try:
                classified_count = max(0, int(classified))
            except Exception:
                classified_count = 0

        for key in ("llmCalls", "llm_calls"):
            value = pipeline.get(key)
            if value is not None:
                try:
                    pipeline_calls = max(0, int(value))
                    break
                except Exception:
                    pass

    observed_calls = 0
    if metadata_calls is not None:
        observed_calls = max(observed_calls, metadata_calls)
    if pipeline_calls is not None:
        observed_calls = max(observed_calls, pipeline_calls)

    if assume_full_llm_when_missing:
        observed_calls = max(observed_calls, classified_count)

    return observed_calls


def compare_outputs(baseline: Dict[str, Any], optimized: Dict[str, Any]) -> Dict[str, Any]:
    """Compare baseline and optimized outputs and compute quality metrics.

    Args:
        baseline: Full LLM pipeline output
        optimized: Selective LLM pipeline output

    Returns:
        Dictionary with quality metrics:
        - core_overlap: Baseline coverage of technology IDs preserved in optimized output (0-1)
        - leader_coverage: Coverage of baseline leader IDs (top market-score set) (0-1)
        - watchlist_recall: Coverage of trending/watchlist technologies (0-1)
        - llm_call_reduction: Percentage reduction in LLM calls (0-1)
        - total_baseline: Number of technologies in baseline
        - total_optimized: Number of technologies in optimized
        - missing_from_optimized: List of IDs present in baseline but not optimized
        - added_in_optimized: List of IDs present in optimized but not baseline
    """
    baseline_techs = baseline.get("technologies", [])
    optimized_techs = optimized.get("technologies", [])
    baseline_watchlist_techs = baseline.get("watchlist", [])
    optimized_watchlist_techs = optimized.get("watchlist", [])

    # Extract IDs for comparison
    baseline_ids = {t.get("id") for t in baseline_techs if t.get("id")}
    optimized_ids = {t.get("id") for t in optimized_techs if t.get("id")}

    # Compute core overlap as baseline coverage.
    # This is robust when optimized intentionally returns more items than baseline.
    intersection = baseline_ids & optimized_ids
    core_overlap = len(intersection) / len(baseline_ids) if baseline_ids else 1.0

    # Compute missing and added
    missing_from_optimized = sorted(baseline_ids - optimized_ids)
    added_in_optimized = sorted(optimized_ids - baseline_ids)

    # Compute leader coverage.
    # Prefer top market-score leaders; fallback to adopt ring leaders.
    scored_leaders = []
    for tech in baseline_techs:
        tech_id = tech.get("id")
        if not tech_id:
            continue
        try:
            score = float(tech.get("marketScore", 0.0))
        except Exception:
            score = 0.0
        scored_leaders.append((str(tech_id), score))

    if scored_leaders:
        scored_leaders.sort(key=lambda pair: pair[1], reverse=True)
        top_n = max(1, min(5, len(scored_leaders)))
        baseline_leaders = {tech_id for tech_id, _ in scored_leaders[:top_n]}
    else:
        baseline_leaders = {t.get("id") for t in baseline_techs if t.get("ring") == "adopt" and t.get("id")}

    leader_coverage = len(baseline_leaders & optimized_ids) / len(baseline_leaders) if baseline_leaders else 1.0

    # Compute watchlist recall (prefer explicit watchlist section, fallback to trending-up items)
    baseline_watchlist = {t.get("id") for t in baseline_watchlist_techs if t.get("id")}
    optimized_watchlist = {t.get("id") for t in optimized_watchlist_techs if t.get("id")}
    if not baseline_watchlist:
        baseline_watchlist = {t.get("id") for t in baseline_techs if t.get("trend") == "up" and t.get("id")}
    if not optimized_watchlist:
        optimized_watchlist = {t.get("id") for t in optimized_techs if t.get("trend") == "up" and t.get("id")}
    watchlist_recall = len(baseline_watchlist & optimized_watchlist) / len(baseline_watchlist) if baseline_watchlist else 1.0

    # Compute LLM call reduction
    baseline_calls = _extract_llm_calls(baseline, assume_full_llm_when_missing=True)
    optimized_calls = _extract_llm_calls(optimized, assume_full_llm_when_missing=False)
    if baseline_calls > 0:
        llm_call_reduction = (baseline_calls - optimized_calls) / baseline_calls
    else:
        llm_call_reduction = 0.0

    baseline_ring_map = {
        t.get("id"): t.get("ring", "unknown")
        for t in baseline_techs
        if t.get("id")
    }
    filtered_by_ring: Dict[str, int] = {}
    for tech_id in missing_from_optimized:
        ring = str(baseline_ring_map.get(tech_id, "unknown"))
        filtered_by_ring[ring] = filtered_by_ring.get(ring, 0) + 1

    report = {
        "core_overlap": round(core_overlap, 4),
        "leader_coverage": round(leader_coverage, 4),
        "watchlist_recall": round(watchlist_recall, 4),
        "llm_call_reduction": round(llm_call_reduction, 4),
        "total_baseline": len(baseline_techs),
        "total_optimized": len(optimized_techs),
        "total_baseline_watchlist": len(baseline_watchlist_techs),
        "total_optimized_watchlist": len(optimized_watchlist_techs),
        "filtered_count": len(missing_from_optimized),
        "added_count": len(added_in_optimized),
        "filtered_by_ring": filtered_by_ring,
        "filtered_sample": missing_from_optimized[:10],
        "missing_from_optimized": missing_from_optimized,
        "added_in_optimized": added_in_optimized,
    }

    logger.info(
        "Shadow eval complete | core_overlap=%s leader_coverage=%s watchlist_recall=%s "
        "llm_reduction=%s baseline=%s optimized=%s",
        report["core_overlap"],
        report["leader_coverage"],
        report["watchlist_recall"],
        report["llm_call_reduction"],
        report["total_baseline"],
        report["total_optimized"],
    )

    return report


def write_report(report: Dict[str, Any], output_path: Path) -> None:
    """Write shadow eval report to JSON file.

    Args:
        report: Quality metrics dictionary
        output_path: Path to write JSON file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    logger.info("Shadow eval report written to %s", output_path)


def meets_quality_thresholds(report: Dict[str, Any], thresholds: Dict[str, float]) -> bool:
    """Check if report meets all quality thresholds.

    Args:
        report: Quality metrics from compare_outputs
        thresholds: Dictionary of metric_name -> minimum_value

    Returns:
        True if all thresholds are met, False otherwise
    """
    for metric, min_value in thresholds.items():
        actual_value = report.get(metric, 0.0)
        if actual_value < min_value:
            logger.warning(
                "Quality threshold not met | metric=%s required=%s actual=%s",
                metric,
                min_value,
                actual_value,
            )
            return False

    logger.info("All quality thresholds met")
    return True


# Default quality thresholds for go/no-go decision
DEFAULT_THRESHOLDS = {
    "core_overlap": 0.85,
    "leader_coverage": 0.95,
    "watchlist_recall": 0.80,
    "llm_call_reduction": 0.60,
}
