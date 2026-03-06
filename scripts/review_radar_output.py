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
]


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
    for item in technologies:
        ring = str(item.get("ring", ""))
        score = _safe_float(item.get("marketScore"))
        signal_names = _non_zero_signal_names(item)

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
    if len(suspicious_lines) == 1:
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
