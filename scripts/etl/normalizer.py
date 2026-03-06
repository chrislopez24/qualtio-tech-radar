"""Normalizer module for merging signals from multiple sources"""

import re
from collections import defaultdict
from typing import List, Dict, Optional

from etl.models import TechnologySignal

SOURCE_WEIGHTS = {
    "github_trending": 1.0,
    "hackernews": 0.8,
}

ALIAS_MAP = {
    "react.js": "react",
    "reactjs": "react",
    "vue.js": "vue",
    "vuejs": "vue",
    "angular.js": "angular",
    "angularjs": "angular",
    "node.js": "node",
    "nodejs": "node",
    "machine-learning": "machine learning",
    "machine_learning": "machine learning",
    "deep-learning": "deep learning",
    "deep_learning": "deep learning",
    "nextjs": "next",
    "nuxtjs": "nuxt",
    "sveltejs": "svelte",
    "denojs": "deno",
    "golang": "go",
    "gcp": "google cloud",
    "aws": "amazon web services",
}


def normalize_name(name: str) -> str:
    """Normalize technology name: lowercase, strip, normalize separators"""
    if not name:
        return ""

    normalized = name.lower().strip()

    normalized = re.sub(r"[-_]+", " ", normalized)

    normalized = re.sub(r"\s+", " ", normalized)

    normalized = normalized.strip()

    return ALIAS_MAP.get(normalized, normalized)


def get_source_weight(source: str) -> float:
    """Get weight for a source"""
    return SOURCE_WEIGHTS.get(source, 0.5)


def normalize_signals(signals: List[TechnologySignal]) -> List[TechnologySignal]:
    """Merge signals from multiple sources into canonical form"""
    if not signals:
        return []

    canonical_signals: Dict[str, Dict] = defaultdict(lambda: {
        "signals": [],
        "weighted_score": 0.0,
        "total_weight": 0.0,
    })

    for signal in signals:
        normalized_name = normalize_name(signal.name)

        if not normalized_name:
            continue

        weight = get_source_weight(signal.source)

        canonical_signals[normalized_name]["signals"].append(signal)
        canonical_signals[normalized_name]["weighted_score"] += signal.score * weight
        canonical_signals[normalized_name]["total_weight"] += weight

    result = []
    for name, data in canonical_signals.items():
        original_signals = data["signals"]
        if not original_signals:
            continue

        first_signal = original_signals[0]
        total_weight = data.get("total_weight", 1)
        score = data["weighted_score"] / total_weight

        merged_signal = TechnologySignal(
            name=name,
            source="merged",
            signal_type="merged",
            score=score,
            raw_data={
                "sources": [s.source for s in original_signals],
                "original_scores": [s.score for s in original_signals],
                "merged_from": len(original_signals),
            }
        )

        result.append(merged_signal)

    return result
