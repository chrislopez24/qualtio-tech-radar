"""Shadow quality evaluator for comparing baseline and optimized ETL outputs

This module provides quality metrics to validate that the optimized (selective LLM)
pipeline produces similar results to the baseline (full LLM) pipeline.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple

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


LEADER_PROMOTION_RUNS = 3


def select_top_leaders(technologies: List[Dict[str, Any]], top_n: int = 5) -> Set[str]:
    """Select leader IDs using market-score ranking with adopt-ring fallback."""
    scored_leaders: List[Tuple[str, float]] = []
    for tech in technologies:
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
        bounded_top_n = max(1, min(top_n, len(scored_leaders)))
        return {tech_id for tech_id, _ in scored_leaders[:bounded_top_n]}

    return {str(t.get("id")) for t in technologies if t.get("ring") == "adopt" and t.get("id")}


def update_leader_stability_state(
    previous_state: Dict[str, Any] | None,
    observed_leaders: Set[str],
    run_id: str,
    promotion_runs: int = LEADER_PROMOTION_RUNS,
) -> Dict[str, Any]:
    """Update stable leader set using consecutive-run candidate promotion.

    Rules:
    - bootstrap: if no prior stable leaders, initialize with observed leaders
    - candidate changes are tracked per leader_id + change_type
    - candidate count increments only when same change is observed in consecutive evaluations
    - candidates missing in current run are dropped (reset)
    - changes are promoted into stable leaders once count reaches promotion_runs
    """
    prev_state = previous_state or {}
    prev_stable = set(prev_state.get("stable_leaders") or [])
    if not prev_stable:
        prev_stable = set(observed_leaders)

    prev_candidates: Dict[str, Dict[str, Any]] = dict(prev_state.get("candidate_changes") or {})

    added = observed_leaders - prev_stable
    removed = prev_stable - observed_leaders

    observed_change_keys: Dict[str, Tuple[str, str]] = {}
    for leader_id in sorted(added):
        observed_change_keys[f"{leader_id}:added"] = (leader_id, "added")
    for leader_id in sorted(removed):
        observed_change_keys[f"{leader_id}:removed"] = (leader_id, "removed")

    next_candidates: Dict[str, Dict[str, Any]] = {}
    for key, (leader_id, change_type) in observed_change_keys.items():
        previous = prev_candidates.get(key)
        previous_count = int(previous.get("consecutive_count", 0)) if previous else 0
        next_candidates[key] = {
            "leader_id": leader_id,
            "change_type": change_type,
            "consecutive_count": previous_count + 1,
            "first_seen_run": previous.get("first_seen_run", run_id) if previous else run_id,
            "last_seen_run": run_id,
        }

    next_stable = set(prev_stable)
    promoted: List[Dict[str, str]] = []
    remaining_candidates: Dict[str, Dict[str, Any]] = {}

    for key, candidate in next_candidates.items():
        if int(candidate.get("consecutive_count", 0)) >= promotion_runs:
            leader_id = str(candidate["leader_id"])
            change_type = str(candidate["change_type"])
            if change_type == "added":
                next_stable.add(leader_id)
            else:
                next_stable.discard(leader_id)
            promoted.append({"leader_id": leader_id, "change_type": change_type})
        else:
            remaining_candidates[key] = candidate

    return {
        "stable_leaders": sorted(next_stable),
        "candidate_changes": remaining_candidates,
        "promoted_changes": promoted,
        "last_run_id": run_id,
        "promotion_runs": promotion_runs,
    }


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
    baseline_leaders = select_top_leaders(baseline_techs)
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


def classify_quality_gate(
    report: Dict[str, Any],
    thresholds: Dict[str, float],
    leader_state: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Classify quality gate status and provide operational guidance."""
    failed_metrics: Dict[str, Dict[str, float]] = {}
    for metric, min_value in thresholds.items():
        actual_value = float(report.get(metric, 0.0))
        if actual_value < min_value:
            failed_metrics[metric] = {
                "required": float(min_value),
                "actual": actual_value,
            }

    candidate_changes = (leader_state or {}).get("candidate_changes") or {}
    promoted_changes = (leader_state or {}).get("promoted_changes") or []

    if failed_metrics:
        status = "fail"
        next_action = "investigate-quality-regression"
    elif candidate_changes:
        status = "warn"
        next_action = "await-stable-leader-transition"
    else:
        status = "pass"
        next_action = "rollout-approved"

    return {
        "status": status,
        "next_action": next_action,
        "failed_metrics": failed_metrics,
        "leader_transition_summary": {
            "candidate_count": len(candidate_changes),
            "promoted_count": len(promoted_changes),
        },
    }


def build_shadow_eval_report(
    metrics_report: Dict[str, Any],
    thresholds: Dict[str, float],
    leader_state: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """Merge metrics, gate classification, and leader-state context."""
    gate = classify_quality_gate(metrics_report, thresholds, leader_state)

    merged = dict(metrics_report)
    merged["gate_status"] = gate["status"]
    merged["next_action"] = gate["next_action"]
    merged["failed_metrics"] = gate["failed_metrics"]
    merged["leader_transition_summary"] = gate["leader_transition_summary"]
    merged["candidate_changes"] = (leader_state or {}).get("candidate_changes", {})
    merged["stable_leaders"] = (leader_state or {}).get("stable_leaders", [])
    return merged


def meets_quality_thresholds(report: Dict[str, Any], thresholds: Dict[str, float]) -> bool:
    """Check if report meets all quality thresholds.

    Args:
        report: Quality metrics from compare_outputs
        thresholds: Dictionary of metric_name -> minimum_value

    Returns:
        True if all thresholds are met, False otherwise
    """
    gate = classify_quality_gate(report, thresholds)
    if gate["status"] == "fail":
        for metric, values in gate["failed_metrics"].items():
            logger.warning(
                "Quality threshold not met | metric=%s required=%s actual=%s",
                metric,
                values["required"],
                values["actual"],
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
