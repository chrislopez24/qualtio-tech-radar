"""Generate a compact human-review summary for radar output artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from etl.ai_filter import is_resource_like_repository


REQUIRED_SUMMARY_KEYS = [
    "inputFile",
    "updatedAt",
    "shadowStatus",
    "counts",
    "quadrantDistribution",
    "ringDistribution",
    "topTechnologies",
    "newlyAdded",
    "dropped",
    "suspiciousItems",
    "publishReadiness",
]

MAX_TRIAL_GITHUB_ONLY_RATIO = 0.5


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _count_distribution(items: List[Dict[str, Any]], key: str, values: List[str]) -> Dict[str, int]:
    counts = {value: 0 for value in values}
    for item in items:
        item_value = item.get(key)
        if item_value in counts:
            counts[str(item_value)] += 1
    return counts


def _top_technologies(items: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
    ranked = sorted(items, key=lambda item: _safe_float(item.get("marketScore")), reverse=True)
    return [
        {
            "id": str(item.get("id", "")),
            "name": str(item.get("name", "")),
            "quadrant": str(item.get("quadrant", "")),
            "ring": str(item.get("ring", "")),
            "marketScore": round(_safe_float(item.get("marketScore")), 2),
            "trend": str(item.get("trend", "")),
        }
        for item in ranked[:limit]
        if item.get("id")
    ]


def _non_zero_signal_names(item: Dict[str, Any]) -> List[str]:
    signals = item.get("signals", {})
    if not isinstance(signals, dict):
        return []

    names: List[str] = []
    for key in ("ghMomentum", "ghPopularity", "hnHeat", "gh_momentum", "gh_popularity", "hn_heat"):
        if _safe_float(signals.get(key)) > 0:
            canonical = key.replace("_", "")
            if canonical not in names:
                names.append(canonical)
    return names


def _summarize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(item.get("id", "")),
        "name": str(item.get("name", "")),
        "ring": str(item.get("ring", "")),
        "marketScore": round(_safe_float(item.get("marketScore")), 2),
    }


def _editorial_flags(item: Dict[str, Any]) -> List[str]:
    return [str(flag) for flag in item.get("editorialFlags", []) if flag]


def _extract_signal_values(item: Dict[str, Any]) -> Dict[str, float]:
    signals = item.get("signals", {})
    if not isinstance(signals, dict):
        signals = {}
    return {
        "ghMomentum": _safe_float(signals.get("ghMomentum", signals.get("gh_momentum", 0))),
        "ghPopularity": _safe_float(signals.get("ghPopularity", signals.get("gh_popularity", 0))),
        "hnHeat": _safe_float(signals.get("hnHeat", signals.get("hn_heat", 0))),
    }


def _is_github_only_signal(item: Dict[str, Any]) -> bool:
    evidence_summary = item.get("evidenceSummary")
    if isinstance(evidence_summary, dict) and "githubOnly" in evidence_summary:
        return bool(evidence_summary.get("githubOnly"))

    source_coverage = item.get("sourceCoverage")
    if source_coverage is not None:
        try:
            if int(source_coverage) > 1:
                return False
        except (TypeError, ValueError):
            pass

    signal_values = _extract_signal_values(item)
    has_github_signal = signal_values["ghMomentum"] > 0 or signal_values["ghPopularity"] > 0
    has_hn_signal = signal_values["hnHeat"] > 0
    return has_github_signal and not has_hn_signal


def _extract_source_coverage(item: Dict[str, Any]) -> int:
    value = item.get("sourceCoverage")
    if value is not None:
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return 0
    if _is_github_only_signal(item):
        return 1
    signal_values = _extract_signal_values(item)
    coverage = 0
    if signal_values["ghMomentum"] > 0 or signal_values["ghPopularity"] > 0:
        coverage += 1
    if signal_values["hnHeat"] > 0:
        coverage += 1
    return coverage


def build_review_summary(payload: Dict[str, Any], input_name: str) -> Dict[str, Any]:
    technologies = payload.get("technologies", [])
    watchlist = payload.get("watchlist", [])
    meta = payload.get("meta", {}) if isinstance(payload.get("meta"), dict) else {}
    pipeline = meta.get("pipeline", {}) if isinstance(meta.get("pipeline"), dict) else {}
    shadow_gate = meta.get("shadowGate", {}) if isinstance(meta.get("shadowGate"), dict) else {}

    top_technologies = _top_technologies(technologies, limit=10)
    newly_added = list(pipeline.get("topAdded", [])) if isinstance(pipeline.get("topAdded"), list) else []
    dropped = list(pipeline.get("topDropped", [])) if isinstance(pipeline.get("topDropped"), list) else []

    low_signal_strong_rings = []
    single_weak_signal = []
    resource_like_strong_rings = []
    github_only_signals = []
    github_only_strong_rings = []
    trial_items = []
    trial_github_only = []
    editorially_invalid = []
    missing_evidence_count = 0
    quadrant_override_count = 0
    for item in technologies:
        ring = str(item.get("ring", ""))
        score = _safe_float(item.get("marketScore"))
        signal_names = _non_zero_signal_names(item)
        github_only = _is_github_only_signal(item)
        editorial_flags = _editorial_flags(item)

        missing_evidence_count += int("missingEvidence" in editorial_flags)
        quadrant_override_count += int("quadrantMismatch" in editorial_flags)
        if str(item.get("editorialStatus", "")).lower() == "invalid":
            summarized = _summarize_item(item)
            summarized["reasons"] = editorial_flags
            editorially_invalid.append(summarized)

        if (ring == "adopt" and score < 80.0) or (ring == "trial" and score < 60.0):
            low_signal_strong_rings.append(_summarize_item(item))

        if len(signal_names) == 1 and score < 60.0:
            summarized = _summarize_item(item)
            summarized["signal"] = signal_names[0]
            single_weak_signal.append(summarized)

        if ring in {"adopt", "trial"} and is_resource_like_repository(
            str(item.get("id", "")),
            str(item.get("description", "")),
        ):
            resource_like_strong_rings.append(_summarize_item(item))

        if github_only:
            github_only_signals.append(_summarize_item(item))
            if ring in {"adopt", "trial"}:
                github_only_strong_rings.append(_summarize_item(item))
            if ring == "trial":
                trial_github_only.append(_summarize_item(item))

        if ring == "trial":
            trial_items.append(item)

    total_technologies = len(technologies)
    github_only_ratio = (len(github_only_signals) / total_technologies) if total_technologies else 0.0
    trial_github_only_ratio = (len(trial_github_only) / len(trial_items)) if trial_items else 0.0
    missing_source_coverage_by_quadrant = sorted(
        {
            str(item.get("quadrant", ""))
            for item in technologies
            if str(item.get("quadrant", "")) and _extract_source_coverage(item) < 2
        }
    )

    editorial_recommendations: List[str] = []
    if github_only_ratio >= 0.5:
        editorial_recommendations.append(
            "High GitHub-only signal ratio detected; review scoring weights and add non-GitHub validation before publication."
        )
    if github_only_strong_rings:
        editorial_recommendations.append(
            "Adopt/trial contains GitHub-only items; tighten strong-ring admission criteria for mono-source technologies."
        )
    if resource_like_strong_rings:
        editorial_recommendations.append(
            "Resource-like repositories still appear in strong rings; strengthen editorial filters for books/awesome/tutorial/reference repositories."
        )
    if low_signal_strong_rings:
        editorial_recommendations.append(
            "Strong rings include low-score entries; revisit ring thresholds and promotion logic."
        )
    if missing_evidence_count:
        editorial_recommendations.append(
            "Missing evidence flags are present; repair or remove invalid items before publication."
        )
    if quadrant_override_count:
        editorial_recommendations.append(
            "Quadrant mismatch flags are present; review semantic classification overrides before publication."
        )
    if missing_source_coverage_by_quadrant:
        editorial_recommendations.append(
            "Some quadrants still lack multi-source corroboration; review source coverage before publication."
        )

    publish_status = "pass"
    publish_reasons: List[str] = []
    if missing_evidence_count:
        publish_status = "fail"
        publish_reasons.append("Missing evidence invalidates one or more published items.")
    if any(item.get("ring") == "adopt" for item in github_only_strong_rings):
        publish_status = "fail"
        publish_reasons.append("Adopt contains GitHub-only items.")
    if trial_github_only_ratio > MAX_TRIAL_GITHUB_ONLY_RATIO:
        publish_status = "fail"
        publish_reasons.append("Trial exceeds acceptable GitHub-only ratio.")
    elif publish_status == "pass" and missing_source_coverage_by_quadrant:
        publish_status = "warn"
        publish_reasons.append("Some quadrants still lack adequate source coverage.")

    return {
        "inputFile": input_name,
        "updatedAt": payload.get("updatedAt"),
        "shadowStatus": shadow_gate.get("status"),
        "counts": {
            "technologies": len(technologies),
            "watchlist": len(watchlist) if isinstance(watchlist, list) else 0,
        },
        "quadrantDistribution": _count_distribution(
            technologies,
            "quadrant",
            ["platforms", "techniques", "tools", "languages"],
        ),
        "ringDistribution": _count_distribution(
            technologies,
            "ring",
            ["adopt", "trial", "assess", "hold"],
        ),
        "topTechnologies": top_technologies,
        "newlyAdded": newly_added[:10],
        "dropped": dropped[:10],
        "suspiciousItems": {
            "repairedDescriptions": int(pipeline.get("repairedDescriptions", 0) or 0),
            "lowSignalStrongRings": low_signal_strong_rings[:10],
            "singleWeakSignal": single_weak_signal[:10],
            "resourceLikeStrongRings": resource_like_strong_rings[:10],
            "githubOnlySignals": github_only_signals[:10],
            "githubOnlyStrongRings": github_only_strong_rings[:10],
            "githubOnlyRatio": round(github_only_ratio, 4),
            "trialGithubOnlyRatio": round(trial_github_only_ratio, 4),
            "missingEvidenceCount": missing_evidence_count,
            "quadrantOverrideCount": quadrant_override_count,
            "editoriallyInvalid": editorially_invalid[:10],
            "missingSourceCoverageByQuadrant": missing_source_coverage_by_quadrant,
            "editorialRecommendations": editorial_recommendations,
        },
        "publishReadiness": {
            "status": publish_status,
            "reasons": publish_reasons,
        },
    }


def validate_review_summary(summary: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    for key in REQUIRED_SUMMARY_KEYS:
        if key not in summary:
            errors.append(f"missing: {key}")
    return errors


def render_markdown(summary: Dict[str, Any]) -> str:
    top_lines = [
        f"- `{item['name']}` `{item['ring']}` `{item['marketScore']}`"
        for item in summary["topTechnologies"][:10]
    ] or ["- None"]

    added_lines = [
        f"- `{item['name']}` `{item['ring']}` `{item['marketScore']}`"
        for item in summary["newlyAdded"][:10]
    ] or ["- None"]

    dropped_lines = [
        f"- `{item['name']}` `{item['ring']}` `{item['marketScore']}`"
        for item in summary["dropped"][:10]
    ] or ["- None"]

    suspicious = summary["suspiciousItems"]
    suspicious_lines = []
    suspicious_lines.append(f"- Repaired descriptions: {suspicious['repairedDescriptions']}")
    suspicious_lines.extend(
        f"- Low-signal strong ring: `{item['name']}` `{item['ring']}` `{item['marketScore']}`"
        for item in suspicious["lowSignalStrongRings"]
    )
    suspicious_lines.extend(
        f"- Single weak signal: `{item['name']}` via `{item['signal']}`"
        for item in suspicious["singleWeakSignal"]
    )
    suspicious_lines.extend(
        f"- Resource-like strong ring: `{item['name']}` `{item['ring']}` `{item['marketScore']}`"
        for item in suspicious.get("resourceLikeStrongRings", [])
    )
    suspicious_lines.extend(
        f"- GitHub-only signal: `{item['name']}` `{item['ring']}` `{item['marketScore']}`"
        for item in suspicious.get("githubOnlySignals", [])
    )
    suspicious_lines.extend(
        f"- GitHub-only strong ring: `{item['name']}` `{item['ring']}` `{item['marketScore']}`"
        for item in suspicious.get("githubOnlyStrongRings", [])
    )
    suspicious_lines.append(f"- GitHub-only ratio: {suspicious.get('githubOnlyRatio', 0.0)}")
    suspicious_lines.append(f"- Trial GitHub-only ratio: {suspicious.get('trialGithubOnlyRatio', 0.0)}")
    suspicious_lines.append(f"- Missing evidence count: {suspicious.get('missingEvidenceCount', 0)}")
    suspicious_lines.append(f"- Quadrant override count: {suspicious.get('quadrantOverrideCount', 0)}")
    suspicious_lines.extend(
        f"- Editorially invalid: `{item['name']}` reasons `{', '.join(item.get('reasons', []))}`"
        for item in suspicious.get("editoriallyInvalid", [])
    )
    suspicious_lines.extend(
        f"- Missing source coverage quadrant: `{quadrant}`"
        for quadrant in suspicious.get("missingSourceCoverageByQuadrant", [])
    )
    suspicious_lines.extend(
        f"- Recommendation: {message}"
        for message in suspicious.get("editorialRecommendations", [])
    )
    if (
        suspicious["repairedDescriptions"] == 0
        and not suspicious["lowSignalStrongRings"]
        and not suspicious["singleWeakSignal"]
        and not suspicious.get("resourceLikeStrongRings", [])
        and not suspicious.get("githubOnlySignals", [])
        and not suspicious.get("githubOnlyStrongRings", [])
        and suspicious.get("missingEvidenceCount", 0) == 0
        and suspicious.get("quadrantOverrideCount", 0) == 0
        and not suspicious.get("editoriallyInvalid", [])
        and not suspicious.get("missingSourceCoverageByQuadrant", [])
        and not suspicious.get("editorialRecommendations", [])
    ):
        suspicious_lines.append("- No suspicious items detected by current heuristics")

    quadrant_distribution = " / ".join(
        f"{key} {value}" for key, value in summary["quadrantDistribution"].items()
    )
    ring_distribution = " / ".join(
        f"{key} {value}" for key, value in summary["ringDistribution"].items()
    )

    lines = [
        "## Radar Review Summary",
        "",
        f"- Input: `{summary['inputFile']}`",
        f"- Updated: `{summary['updatedAt']}`",
        f"- Shadow gate: `{summary['shadowStatus']}`",
        f"- Publish readiness: `{summary['publishReadiness']['status']}`",
        f"- Counts: technologies `{summary['counts']['technologies']}`, watchlist `{summary['counts']['watchlist']}`",
        f"- Quadrants: {quadrant_distribution}",
        f"- Rings: {ring_distribution}",
        "",
        "### Top 10 By Market Score",
        *top_lines,
        "",
        "### Newly Added",
        *added_lines,
        "",
        "### Dropped",
        *dropped_lines,
        "",
        "### Suspicious Items",
        *suspicious_lines,
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a compact radar review summary.")
    parser.add_argument("--input", required=True, help="Path to data.ai.json")
    parser.add_argument("--output-json", default="artifacts/review-summary.json", help="Path to write JSON review summary")
    parser.add_argument("--output-md", default="artifacts/review-summary.md", help="Path to write Markdown review summary")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_json = Path(args.output_json)
    output_md = Path(args.output_md)

    payload = json.loads(input_path.read_text())
    summary = build_review_summary(payload, input_name=input_path.name)
    errors = validate_review_summary(summary)
    if errors:
        for error in errors:
            print(error)
        return 1

    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(summary, indent=2))
    output_md.write_text(render_markdown(summary))
    print(render_markdown(summary))
    return 1 if summary["publishReadiness"]["status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
