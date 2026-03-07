"""Output generator for creating sanitized public radar output."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List


FIELDS_TO_REMOVE_FOR_PUBLIC = [
    "repoNames",
    "internalNote",
    "rawData",
    "source_summary",
    "signal_freshness",
    "source_coverage",
    "source_freshness",
    "evidence_summary",
    "why_this_ring",
]

OPTIONAL_PUBLIC_FIELD_ALIASES = {
    "source_coverage": "sourceCoverage",
    "source_freshness": "sourceFreshness",
    "evidence_summary": "evidenceSummary",
    "why_this_ring": "whyThisRing",
}


def sanitize_for_public(technology: Dict[str, Any]) -> Dict[str, Any]:
    """Remove internal/sensitive fields from technology for public output"""
    sanitized = {}
    for key, value in technology.items():
        if key not in FIELDS_TO_REMOVE_FOR_PUBLIC:
            sanitized[key] = value

    source_summary = technology.get("sourceSummary") or technology.get("source_summary")
    if source_summary:
        sanitized["sourceSummary"] = source_summary

    signal_freshness = technology.get("signalFreshness") or technology.get("signal_freshness")
    if signal_freshness:
        sanitized["signalFreshness"] = signal_freshness

    for source_key, target_key in OPTIONAL_PUBLIC_FIELD_ALIASES.items():
        if target_key in sanitized:
            continue
        value = technology.get(target_key, technology.get(source_key))
        if value is not None:
            sanitized[target_key] = value

    return sanitized


def generate_outputs(
    technologies: List[Dict[str, Any]],
    output_dir: Path
) -> Dict[str, Any]:
    """Generate public (sanitized) output file"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().isoformat()

    sanitized_technologies = [
        sanitize_for_public(tech) for tech in technologies
    ]

    public_payload = {
        "updatedAt": timestamp,
        "technologies": sanitized_technologies
    }

    public_file = output_dir / "data.ai.json"
    with open(public_file, "w") as f:
        json.dump(public_payload, f, indent=2)

    return {
        "public_payload": public_payload,
    }
