from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from etl.canonical.resolver import resolve_market_entities
from etl.config import ETLConfig
from etl.contracts import EditorialDecisionBundle
from etl.discovery.collector import DiscoveryCollector, build_default_sources
from etl.editorial_llm.harmonizer import harmonize_decisions
from etl.editorial_llm.lane_editor import decide_lane
from etl.lanes.packer import pack_lanes
from etl.publish.publisher import publish_radar
from etl.signals.snapshot_builder import build_market_snapshot
from etl.sources.deps_dev import DepsDevSource
from etl.sources.osv_source import OSVSource
from etl.validation_enrichment import enrich_market_entities_with_validation


def run_market_radar_pipeline(config: ETLConfig, source_names: set[str] | None = None) -> dict[str, Any]:
    collector = DiscoveryCollector(build_default_sources(config, source_names=source_names))
    raw_records = collector.collect()
    market_entities = resolve_market_entities(raw_records)
    market_entities = enrich_market_entities_with_validation(
        market_entities,
        deps_dev_source=DepsDevSource(config.sources.deps_dev),
        osv_source=OSVSource(config.sources.osv),
    )
    snapshot = build_market_snapshot(market_entities)
    lane_packs = pack_lanes(snapshot)

    decisions = [
        decide_lane(lane_input, max_items=lane_budget(config.distribution.target_total, len(lane_packs)))
        for lane_input in lane_packs.values()
    ]
    bundle = EditorialDecisionBundle(decisions=decisions)
    harmonized = harmonize_decisions(bundle, target_total=config.distribution.target_total)
    harmonized.setdefault("meta", {}).setdefault("pipeline", {})["collected"] = len(raw_records)

    return build_pipeline_result(
        raw_records=raw_records,
        snapshot=[entity.model_dump(mode="json") for entity in snapshot],
        lane_packs={lane: pack.model_dump(mode="json") for lane, pack in lane_packs.items()},
        decisions=bundle,
        harmonized=harmonized,
        public_preview=publish_radar(harmonized, Path("artifacts/data.ai.preview.json")),
    )


def build_pipeline_result(
    raw_records: list[dict[str, Any]],
    snapshot: list[dict[str, Any]],
    lane_packs: dict[str, dict[str, Any]],
    decisions: EditorialDecisionBundle,
    harmonized: dict[str, Any],
    public_preview: dict[str, Any],
) -> dict[str, Any]:
    return {
        "raw_records": raw_records,
        "snapshot": snapshot,
        "lane_packs": lane_packs,
        "decisions": decisions.model_dump(mode="json"),
        "harmonized": harmonized,
        "public_preview": public_preview,
    }


def lane_budget(target_total: int, lane_count: int) -> int:
    return max(3, math.ceil(target_total / max(1, lane_count)))


def write_internal_artifacts(result: dict[str, Any], artifacts_dir: Path = Path("artifacts")) -> None:
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    artifact_map = {
        "market-snapshot.json": result["snapshot"],
        "lane-packs.json": result["lane_packs"],
        "editorial-decisions.json": result["decisions"],
        "editorial-harmonized.json": result["harmonized"],
    }
    for filename, payload in artifact_map.items():
        (artifacts_dir / filename).write_text(json.dumps(payload, indent=2) + "\n")
