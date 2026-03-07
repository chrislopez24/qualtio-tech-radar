"""Shadow quality evaluator for comparing baseline and optimized ETL outputs

This module provides quality metrics to validate that the optimized (selective LLM)
pipeline produces similar results to the baseline (full LLM) pipeline.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Set, Tuple

from etl.ai_filter import is_resource_like_repository

logger = logging.getLogger(__name__)

MAX_TRIAL_GITHUB_ONLY_RATIO = 0.5


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


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def deserialize_leader_state(raw_state: Any) -> Dict[str, Any]:
    """Normalize persisted leader state into stable internal snake_case shape."""
    source = raw_state if isinstance(raw_state, dict) else {}

    raw_stable = source.get("stable_leaders")
    if raw_stable is None:
        raw_stable = source.get("stableLeaders", [])
    stable_leaders = sorted({str(leader_id) for leader_id in (raw_stable or []) if leader_id})

    raw_candidates = source.get("candidate_changes")
    if raw_candidates is None:
        raw_candidates = source.get("candidateChanges", {})
    raw_candidates = raw_candidates if isinstance(raw_candidates, dict) else {}

    normalized_candidates: Dict[str, Dict[str, Any]] = {}
    for candidate_key in sorted(raw_candidates.keys()):
        candidate_value = raw_candidates.get(candidate_key)
        if not isinstance(candidate_value, dict):
            continue

        leader_id = str(
            candidate_value.get("leader_id")
            or candidate_value.get("leaderId")
            or str(candidate_key).split(":", 1)[0]
        )
        change_type = str(
            candidate_value.get("change_type")
            or candidate_value.get("changeType")
            or (str(candidate_key).split(":", 1)[1] if ":" in str(candidate_key) else "added")
        )
        if change_type not in {"added", "removed"}:
            change_type = "added"

        key = f"{leader_id}:{change_type}"
        normalized_candidates[key] = {
            "leader_id": leader_id,
            "change_type": change_type,
            "consecutive_count": max(0, _to_int(candidate_value.get("consecutive_count", candidate_value.get("consecutiveCount", 0)))),
            "first_seen_run": str(candidate_value.get("first_seen_run", candidate_value.get("firstSeenRun", ""))),
            "last_seen_run": str(candidate_value.get("last_seen_run", candidate_value.get("lastSeenRun", ""))),
        }

    raw_promoted = source.get("promoted_changes")
    if raw_promoted is None:
        raw_promoted = source.get("promotedChanges", [])
    raw_promoted = raw_promoted if isinstance(raw_promoted, list) else []

    promoted_changes: List[Dict[str, str]] = []
    for change in raw_promoted:
        if not isinstance(change, dict):
            continue
        leader_id = str(change.get("leader_id") or change.get("leaderId") or "")
        change_type = str(change.get("change_type") or change.get("changeType") or "added")
        if not leader_id:
            continue
        if change_type not in {"added", "removed"}:
            change_type = "added"
        promoted_changes.append({"leader_id": leader_id, "change_type": change_type})
    promoted_changes.sort(key=lambda item: (item["leader_id"], item["change_type"]))

    return {
        "stable_leaders": stable_leaders,
        "candidate_changes": normalized_candidates,
        "promoted_changes": promoted_changes,
        "last_run_id": str(source.get("last_run_id", source.get("lastRunId", ""))),
        "promotion_runs": max(1, _to_int(source.get("promotion_runs", source.get("promotionRuns", LEADER_PROMOTION_RUNS)), LEADER_PROMOTION_RUNS)),
    }


def serialize_leader_state(state: Dict[str, Any] | None) -> Dict[str, Any]:
    """Serialize leader state for deterministic meta.shadowGate.leaderState persistence."""
    normalized = deserialize_leader_state(state)

    serialized_candidates: Dict[str, Dict[str, Any]] = {}
    for key in sorted(normalized["candidate_changes"].keys()):
        candidate = normalized["candidate_changes"][key]
        serialized_candidates[key] = {
            "leaderId": candidate["leader_id"],
            "changeType": candidate["change_type"],
            "consecutiveCount": int(candidate.get("consecutive_count", 0)),
            "firstSeenRun": str(candidate.get("first_seen_run", "")),
            "lastSeenRun": str(candidate.get("last_seen_run", "")),
        }

    return {
        "stableLeaders": list(normalized["stable_leaders"]),
        "candidateChanges": serialized_candidates,
        "promotedChanges": [
            {"leaderId": change["leader_id"], "changeType": change["change_type"]}
            for change in normalized["promoted_changes"]
        ],
        "lastRunId": normalized["last_run_id"],
        "promotionRuns": int(normalized["promotion_runs"]),
    }


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


def _signal_value(entry: Dict[str, Any], *keys: str) -> float:
    signals = entry.get("signals", {})
    if not isinstance(signals, dict):
        return 0.0
    for key in keys:
        if key in signals:
            try:
                return float(signals.get(key) or 0.0)
            except Exception:
                return 0.0
    return 0.0


def _is_github_only_entry(entry: Dict[str, Any]) -> bool:
    evidence_summary = entry.get("evidenceSummary")
    if isinstance(evidence_summary, dict) and "githubOnly" in evidence_summary:
        return bool(evidence_summary.get("githubOnly"))

    source_coverage = entry.get("sourceCoverage")
    if source_coverage is not None:
        try:
            if int(source_coverage) > 1:
                return False
        except Exception:
            pass

    gh_momentum = _signal_value(entry, "ghMomentum", "gh_momentum")
    gh_popularity = _signal_value(entry, "ghPopularity", "gh_popularity")
    hn_heat = _signal_value(entry, "hnHeat", "hn_heat")
    has_github_signal = gh_momentum > 0 or gh_popularity > 0
    return has_github_signal and hn_heat <= 0


def _extract_source_coverage(entry: Dict[str, Any]) -> int:
    value = entry.get("sourceCoverage")
    if value is not None:
        try:
            return max(0, int(value))
        except Exception:
            return 0

    coverage = 0
    if _signal_value(entry, "ghMomentum", "gh_momentum") > 0 or _signal_value(entry, "ghPopularity", "gh_popularity") > 0:
        coverage += 1
    if _signal_value(entry, "hnHeat", "hn_heat") > 0:
        coverage += 1
    return coverage


def _has_missing_evidence(entry: Dict[str, Any]) -> bool:
    flags = {str(flag) for flag in entry.get("editorialFlags", []) if flag}
    if "missingEvidence" in flags:
        return True

    source_coverage = _extract_source_coverage(entry)
    evidence = entry.get("evidence")
    has_evidence = isinstance(evidence, list) and len(evidence) > 0
    return source_coverage > 0 and not has_evidence


def _quadrants_missing_source_coverage(technologies: List[Dict[str, Any]]) -> List[str]:
    quadrants = {
        str(entry.get("quadrant", ""))
        for entry in technologies
        if str(entry.get("quadrant", "")) and _extract_source_coverage(entry) < 2
    }
    return sorted(quadrants)


def _compute_github_bias_metrics(technologies: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not technologies:
        return {
            "github_bias": 0.0,
            "github_only_count": 0,
            "github_only_strong_ring_count": 0,
            "github_only_strong_ring_sample": [],
            "adopt_github_only_count": 0,
            "trial_github_only_ratio": 0.0,
            "editorial_recommendations": [],
        }

    github_only_entries = [entry for entry in technologies if _is_github_only_entry(entry)]
    github_only_strong = [
        entry
        for entry in github_only_entries
        if str(entry.get("ring", "")) in {"adopt", "trial"}
    ]
    github_only_adopt = [
        entry
        for entry in github_only_entries
        if str(entry.get("ring", "")) == "adopt"
    ]
    github_only_trial = [
        entry
        for entry in github_only_entries
        if str(entry.get("ring", "")) == "trial"
    ]
    trial_entries = [
        entry
        for entry in technologies
        if str(entry.get("ring", "")) == "trial"
    ]
    github_bias = len(github_only_entries) / len(technologies)
    trial_github_only_ratio = (len(github_only_trial) / len(trial_entries)) if trial_entries else 0.0

    recommendations: List[str] = []
    if github_bias >= 0.5:
        recommendations.append(
            "High GitHub-only share detected; recalibrate scoring weights and add non-GitHub corroboration before publication."
        )
    if github_only_adopt:
        recommendations.append(
            "GitHub-only entries reached adopt; tighten strong-ring admission for mono-source technologies."
        )
    if trial_github_only_ratio > MAX_TRIAL_GITHUB_ONLY_RATIO:
        recommendations.append(
            "Trial exceeds the allowed GitHub-only ratio; increase corroboration or demote mono-source candidates."
        )

    return {
        "github_bias": round(github_bias, 4),
        "github_only_count": len(github_only_entries),
        "github_only_strong_ring_count": len(github_only_strong),
        "github_only_strong_ring_sample": [str(entry.get("id")) for entry in github_only_strong[:10] if entry.get("id")],
        "adopt_github_only_count": len(github_only_adopt),
        "trial_github_only_ratio": round(trial_github_only_ratio, 4),
        "editorial_recommendations": recommendations,
    }


def _count_editorial_flags(entries: List[Dict[str, Any]]) -> Dict[str, int]:
    missing_evidence = 0
    quadrant_override = 0
    for entry in entries:
        flags = {str(flag) for flag in entry.get("editorialFlags", []) if flag}
        missing_evidence += int("missingEvidence" in flags)
        quadrant_override += int("quadrantMismatch" in flags)
    return {
        "missing_evidence_count": missing_evidence,
        "quadrant_override_count": quadrant_override,
    }


def _extract_metric_inputs(baseline: Dict[str, Any], optimized: Dict[str, Any]) -> Dict[str, Any]:
    """Extract deterministic metric-computation inputs from pipeline outputs."""
    def _filter_entries(entries: Any, *, drop_missing_evidence: bool = False) -> List[Dict[str, Any]]:
        filtered: List[Dict[str, Any]] = []
        for entry in entries if isinstance(entries, list) else []:
            if not isinstance(entry, dict):
                continue
            name = str(entry.get("name") or entry.get("id") or "")
            description = str(entry.get("description") or "")
            if is_resource_like_repository(name, description):
                continue
            if drop_missing_evidence and _has_missing_evidence(entry):
                continue
            filtered.append(entry)
        return filtered

    baseline_techs = _filter_entries(baseline.get("technologies", []), drop_missing_evidence=False)
    optimized_techs = _filter_entries(optimized.get("technologies", []), drop_missing_evidence=False)

    baseline_watchlist_raw = baseline.get("watchlist", [])
    optimized_watchlist_raw = optimized.get("watchlist", [])
    baseline_watchlist_had_explicit_entries = isinstance(baseline_watchlist_raw, list) and len(baseline_watchlist_raw) > 0
    optimized_watchlist_had_explicit_entries = isinstance(optimized_watchlist_raw, list) and len(optimized_watchlist_raw) > 0

    baseline_watchlist_techs = _filter_entries(baseline_watchlist_raw, drop_missing_evidence=True)
    optimized_watchlist_techs = _filter_entries(optimized_watchlist_raw, drop_missing_evidence=True)

    baseline_ids = {str(t.get("id")) for t in baseline_techs if t.get("id")}
    optimized_ids = {str(t.get("id")) for t in optimized_techs if t.get("id")}

    missing_from_optimized = sorted(baseline_ids - optimized_ids)
    added_in_optimized = sorted(optimized_ids - baseline_ids)

    baseline_watchlist = {str(t.get("id")) for t in baseline_watchlist_techs if t.get("id")}
    optimized_watchlist = {str(t.get("id")) for t in optimized_watchlist_techs if t.get("id")}

    if not baseline_watchlist and not baseline_watchlist_had_explicit_entries:
        baseline_watchlist = {str(t.get("id")) for t in baseline_techs if t.get("trend") == "up" and t.get("id")}
    if not optimized_watchlist and not optimized_watchlist_had_explicit_entries:
        optimized_watchlist = {str(t.get("id")) for t in optimized_techs if t.get("trend") == "up" and t.get("id")}

    baseline_ring_map = {
        t.get("id"): t.get("ring", "unknown")
        for t in baseline_techs
        if t.get("id")
    }

    return {
        "baseline_techs": baseline_techs,
        "optimized_techs": optimized_techs,
        "baseline_watchlist_techs": baseline_watchlist_techs,
        "optimized_watchlist_techs": optimized_watchlist_techs,
        "baseline_ids": baseline_ids,
        "optimized_ids": optimized_ids,
        "missing_from_optimized": missing_from_optimized,
        "added_in_optimized": added_in_optimized,
        "baseline_watchlist": baseline_watchlist,
        "optimized_watchlist": optimized_watchlist,
        "baseline_ring_map": baseline_ring_map,
    }


def _apply_leader_policy(
    prev_stable: Set[str],
    next_candidates: Dict[str, Dict[str, Any]],
    promotion_runs: int,
) -> Dict[str, Any]:
    """Promote leader candidate changes and return updated stable/candidate sets."""
    next_stable = set(prev_stable)
    promoted: List[Dict[str, str]] = []
    remaining_candidates: Dict[str, Dict[str, Any]] = {}

    for key in sorted(next_candidates.keys()):
        candidate = next_candidates[key]
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
        "promoted_changes": promoted,
        "remaining_candidates": remaining_candidates,
    }


def _collect_failed_metrics(report: Dict[str, Any], thresholds: Dict[str, float]) -> Dict[str, Dict[str, float]]:
    """Collect threshold breaches for quality-gate classification."""
    failed_metrics: Dict[str, Dict[str, float]] = {}
    for metric, min_value in thresholds.items():
        actual_value = float(report.get(metric, 0.0))
        if actual_value < min_value:
            failed_metrics[metric] = {
                "required": float(min_value),
                "actual": actual_value,
            }
    return failed_metrics


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
    prev_state = deserialize_leader_state(previous_state)
    prev_stable = set(prev_state.get("stable_leaders") or [])
    if not prev_stable:
        prev_stable = set(observed_leaders)

    prev_candidates: Dict[str, Dict[str, Any]] = dict(prev_state.get("candidate_changes") or {})

    added = observed_leaders - prev_stable
    removed = prev_stable - observed_leaders

    observed_change_keys: Dict[str, Tuple[str, str]] = {}
    for leader_id in sorted(str(item) for item in added if item):
        observed_change_keys[f"{leader_id}:added"] = (leader_id, "added")
    for leader_id in sorted(str(item) for item in removed if item):
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

    policy = _apply_leader_policy(prev_stable, next_candidates, promotion_runs)

    return {
        "stable_leaders": policy["stable_leaders"],
        "candidate_changes": policy["remaining_candidates"],
        "promoted_changes": policy["promoted_changes"],
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
    metric_inputs = _extract_metric_inputs(baseline, optimized)

    baseline_techs = metric_inputs["baseline_techs"]
    optimized_techs = metric_inputs["optimized_techs"]
    baseline_watchlist_techs = metric_inputs["baseline_watchlist_techs"]
    optimized_watchlist_techs = metric_inputs["optimized_watchlist_techs"]
    baseline_ids = metric_inputs["baseline_ids"]
    optimized_ids = metric_inputs["optimized_ids"]
    missing_from_optimized = metric_inputs["missing_from_optimized"]
    added_in_optimized = metric_inputs["added_in_optimized"]
    baseline_watchlist = metric_inputs["baseline_watchlist"]
    optimized_watchlist = metric_inputs["optimized_watchlist"]

    # Compute core overlap as baseline coverage.
    # This is robust when optimized intentionally returns more items than baseline.
    intersection = baseline_ids & optimized_ids
    core_overlap = len(intersection) / len(baseline_ids) if baseline_ids else 1.0

    # Compute leader coverage.
    baseline_leaders = select_top_leaders(baseline_techs)
    leader_coverage = len(baseline_leaders & optimized_ids) / len(baseline_leaders) if baseline_leaders else 1.0

    # Compute watchlist recall
    watchlist_recall = len(baseline_watchlist & optimized_watchlist) / len(baseline_watchlist) if baseline_watchlist else 1.0

    # Compute LLM call reduction
    baseline_calls = _extract_llm_calls(baseline, assume_full_llm_when_missing=True)
    optimized_calls = _extract_llm_calls(optimized, assume_full_llm_when_missing=False)
    if baseline_calls > 0:
        llm_call_reduction = (baseline_calls - optimized_calls) / baseline_calls
    else:
        llm_call_reduction = 0.0
    llm_call_reduction = max(0.0, min(1.0, llm_call_reduction))

    filtered_by_ring: Dict[str, int] = {}
    for tech_id in missing_from_optimized:
        ring = str(metric_inputs["baseline_ring_map"].get(tech_id, "unknown"))
        filtered_by_ring[ring] = filtered_by_ring.get(ring, 0) + 1

    optimized_bias = _compute_github_bias_metrics(optimized_techs)
    editorial_flag_counts = _count_editorial_flags(optimized_techs)

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
        "github_bias": optimized_bias["github_bias"],
        "github_only_count": optimized_bias["github_only_count"],
        "github_only_strong_ring_count": optimized_bias["github_only_strong_ring_count"],
        "github_only_strong_ring_sample": optimized_bias["github_only_strong_ring_sample"],
        "adopt_github_only_count": optimized_bias["adopt_github_only_count"],
        "trial_github_only_ratio": optimized_bias["trial_github_only_ratio"],
        "quadrants_missing_source_coverage": _quadrants_missing_source_coverage(optimized_techs),
        "editorial_recommendations": optimized_bias["editorial_recommendations"],
        "missing_evidence_count": editorial_flag_counts["missing_evidence_count"],
        "quadrant_override_count": editorial_flag_counts["quadrant_override_count"],
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
    failed_metrics = _collect_failed_metrics(report, thresholds)

    candidate_changes = (leader_state or {}).get("candidate_changes") or {}
    promoted_changes = (leader_state or {}).get("promoted_changes") or []

    if int(report.get("missing_evidence_count", 0) or 0) > 0:
        status = "fail"
        next_action = "remove-missing-evidence-items"
        next_action_message = "Remove or repair items with missing evidence before rollout."
    elif report.get("adopt_github_only_count", 0):
        status = "fail"
        next_action = "remove-github-only-adopt"
        next_action_message = "Remove GitHub-only items from adopt before rollout."
    elif float(report.get("trial_github_only_ratio", 0.0) or 0.0) > MAX_TRIAL_GITHUB_ONLY_RATIO:
        status = "fail"
        next_action = "reduce-trial-github-only-ratio"
        next_action_message = "Reduce GitHub-only trial ratio before rollout."
    elif failed_metrics:
        status = "fail"
        next_action = "investigate-quality-regression"
        next_action_message = "Investigate quality regression before rollout."
    elif report.get("quadrants_missing_source_coverage"):
        status = "warn"
        next_action = "improve-source-coverage"
        next_action_message = "Improve source coverage in affected quadrants before rollout approval."
    elif candidate_changes:
        status = "warn"
        next_action = "await-stable-leader-transition"
        next_action_message = "Await stable leader transition before rollout approval."
    else:
        status = "pass"
        next_action = "rollout-approved"
        next_action_message = "Quality checks passed and rollout is approved."

    return {
        "status": status,
        "next_action": next_action,
        "next_action_message": next_action_message,
        "next_action_code": next_action,
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
    merged["next_action_message"] = gate["next_action_message"]
    merged["next_action_code"] = gate["next_action_code"]
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
