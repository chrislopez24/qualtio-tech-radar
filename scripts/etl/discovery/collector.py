from __future__ import annotations

import logging
import re
from collections import defaultdict
from typing import Any, Iterable

from etl.canonical.seeds import build_seed_lookup, get_seed_catalog
from etl.config import ETLConfig
from etl.sources.github_trending import GitHubTrendingSource
from etl.sources.hackernews import HackerNewsSource

logger = logging.getLogger(__name__)
SEED_LOOKUP = build_seed_lookup()


class DiscoveryCollector:
    def __init__(self, sources: list[object]):
        self.sources = sources

    def collect(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for source in self.sources:
            source_name = getattr(source, "name", source.__class__.__name__.lower())
            try:
                fetched = source.fetch()
            except Exception as exc:  # pragma: no cover - best effort runtime guard
                logger.warning("Discovery source %s failed: %s", source_name, exc)
                continue

            for item in fetched:
                payload = _coerce_record(item)
                payload["source"] = source_name
                records.append(payload)

        return records


class SeedCatalogSource:
    name = "seed_catalog"

    def fetch(self) -> list[dict[str, Any]]:
        return [
            {
                "name": seed["canonical_name"],
                "ecosystem": seed["ecosystems"][0] if seed.get("ecosystems") else "",
                "topic_family": seed["topic_family"],
                "description": seed.get("description"),
                "source_evidence": [
                    {
                        "source": "seed_catalog",
                        "metric": "curated_presence",
                        "normalized_value": 72.0,
                    }
                ],
                "candidate_reason_inputs": [f"Curated seed for {seed['editorial_kind']} lane coverage."],
            }
            for seed in get_seed_catalog()
        ]


class GitHubTrendingDiscoverySource:
    name = "github_trending"

    def __init__(self, config):
        self.source = GitHubTrendingSource(config)

    def fetch(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for signal in self.source.fetch():
            raw = signal.raw_data or {}
            canonical_seed = _seed_for_github_signal(signal)
            if canonical_seed is None:
                continue

            records.append(
                {
                    "name": canonical_seed["canonical_name"],
                    "ecosystem": "github",
                    "description": raw.get("description"),
                    "candidate_reason_inputs": ["Observed in current GitHub activity window."],
                    "source_evidence": [
                        {
                            "source": "github_trending",
                            "metric": signal.signal_type,
                            "normalized_value": round(float(signal.score) * 10.0, 2),
                            "raw_value": raw.get("stars", 0),
                        }
                    ],
                }
            )
        return records


class HackerNewsDiscoverySource:
    name = "hackernews"

    def __init__(self, config):
        self.source = HackerNewsSource(config, max_stories_scan=500)

    def fetch(self) -> list[dict[str, Any]]:
        mentions: dict[str, list[float]] = defaultdict(list)
        for story in self.source.fetch():
            text = f"{story.title} {story.url}".lower()
            for alias, seed in SEED_LOOKUP.items():
                if _contains_alias(text, alias):
                    mentions[seed["canonical_name"]].append(min(100.0, float(story.points) * 0.5 + story.tech_score * 5.0))

        records: list[dict[str, Any]] = []
        for canonical_name, scores in mentions.items():
            records.append(
                {
                    "name": canonical_name,
                    "ecosystem": "",
                    "candidate_reason_inputs": ["Observed in current Hacker News discussion."],
                    "source_evidence": [
                        {
                            "source": "hackernews",
                            "metric": "discussion_heat",
                            "normalized_value": round(sum(scores) / len(scores), 2),
                            "raw_value": len(scores),
                        }
                    ],
                }
            )
        return records


def build_default_sources(config: ETLConfig, source_names: set[str] | None = None) -> list[object]:
    allowed = source_names or {"seed_catalog", "github_trending", "hackernews"}
    sources: list[object] = []

    if "seed_catalog" in allowed:
        sources.append(SeedCatalogSource())
    if "github_trending" in allowed and config.sources.github_trending.enabled:
        sources.append(GitHubTrendingDiscoverySource(config.sources.github_trending))
    if "hackernews" in allowed and config.sources.hackernews.enabled:
        sources.append(HackerNewsDiscoverySource(config.sources.hackernews))

    return sources


def _coerce_record(item: Any) -> dict[str, Any]:
    if isinstance(item, dict):
        return dict(item)
    if hasattr(item, "__dict__"):
        return dict(vars(item))
    raise TypeError(f"Unsupported discovery record type: {type(item)!r}")


def _contains_alias(text: str, alias: str) -> bool:
    value = str(alias or "").strip().lower()
    if not value:
        return False

    pattern = re.escape(value)
    if value[0].isalnum():
        pattern = rf"(?<![a-z0-9]){pattern}"
    if value[-1].isalnum():
        pattern = rf"{pattern}(?![a-z0-9])"

    return re.search(pattern, text) is not None


def _seed_for_github_signal(signal: Any) -> dict[str, Any] | None:
    raw = getattr(signal, "raw_data", {}) or {}
    candidates = [
        str(raw.get("name") or "").strip().lower(),
        str(raw.get("full_name") or "").strip().lower().split("/")[-1],
        str(getattr(signal, "name", "") or "").strip().lower(),
    ]
    for topic in raw.get("topics", []) or []:
        candidates.append(str(topic).strip().lower())

    for candidate in candidates:
        seed = SEED_LOOKUP.get(candidate)
        if seed is not None:
            return seed
    return None
