"""Shadow quality evaluator for comparing baseline and optimized ETL outputs

This module provides quality metrics to validate that the optimized (selective LLM)
pipeline produces similar results to the baseline (full LLM) pipeline.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Set

logger = logging.getLogger(__name__)


def compare_outputs(baseline: Dict[str, Any], optimized: Dict[str, Any]) -> Dict[str, Any]:
    """Compare baseline and optimized outputs and compute quality metrics.

    Args:
        baseline: Full LLM pipeline output
        optimized: Selective LLM pipeline output

    Returns:
        Dictionary with quality metrics:
        - core_overlap: Jaccard similarity of technology IDs (0-1)
        - leader_coverage: Coverage of high-confidence "adopt" ring technologies (0-1)
        - watchlist_recall: Coverage of trending/watchlist technologies (0-1)
        - llm_call_reduction: Percentage reduction in LLM calls (0-1)
        - total_baseline: Number of technologies in baseline
        - total_optimized: Number of technologies in optimized
        - missing_from_optimized: List of IDs present in baseline but not optimized
        - added_in_optimized: List of IDs present in optimized but not baseline
    """
    baseline_techs = baseline.get("technologies", [])
    optimized_techs = optimized.get("technologies", [])

    # Extract IDs for comparison
    baseline_ids = {t.get("id") for t in baseline_techs if t.get("id")}
    optimized_ids = {t.get("id") for t in optimized_techs if t.get("id")}

    # Compute core overlap (Jaccard similarity)
    intersection = baseline_ids & optimized_ids
    union = baseline_ids | optimized_ids
    core_overlap = len(intersection) / len(union) if union else 1.0

    # Compute missing and added
    missing_from_optimized = sorted(baseline_ids - optimized_ids)
    added_in_optimized = sorted(optimized_ids - baseline_ids)

    # Compute leader coverage (adopt ring technologies)
    baseline_adopt = {t.get("id") for t in baseline_techs if t.get("ring") == "adopt" and t.get("id")}
    optimized_adopt = {t.get("id") for t in optimized_techs if t.get("ring") == "adopt" and t.get("id")}
    leader_coverage = len(baseline_adopt & optimized_adopt) / len(baseline_adopt) if baseline_adopt else 1.0

    # Compute watchlist recall (trending up technologies)
    baseline_watchlist = {t.get("id") for t in baseline_techs if t.get("trend") == "up" and t.get("id")}
    optimized_watchlist = {t.get("id") for t in optimized_techs if t.get("trend") == "up" and t.get("id")}
    watchlist_recall = len(baseline_watchlist & optimized_watchlist) / len(baseline_watchlist) if baseline_watchlist else 1.0

    # Compute LLM call reduction
    baseline_calls = baseline.get("metadata", {}).get("llm_calls", 0)
    optimized_calls = optimized.get("metadata", {}).get("llm_calls", 0)
    if baseline_calls > 0:
        llm_call_reduction = (baseline_calls - optimized_calls) / baseline_calls
    else:
        llm_call_reduction = 0.0

    report = {
        "core_overlap": round(core_overlap, 4),
        "leader_coverage": round(leader_coverage, 4),
        "watchlist_recall": round(watchlist_recall, 4),
        "llm_call_reduction": round(llm_call_reduction, 4),
        "total_baseline": len(baseline_techs),
        "total_optimized": len(optimized_techs),
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
