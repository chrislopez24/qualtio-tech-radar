"""Market-first radar pipeline entrypoint."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from dotenv import load_dotenv

from etl.canonical.resolver import resolve_market_entities
from etl.config import ETLConfig, load_etl_config
from etl.contracts import EditorialDecisionBundle
from etl.discovery.collector import DiscoveryCollector, build_default_sources
from etl.editorial_llm.harmonizer import harmonize_decisions
from etl.editorial_llm.lane_editor import decide_lane
from etl.lanes.packer import pack_lanes
from etl.publish.publisher import publish_radar
from etl.signals.snapshot_builder import build_market_snapshot

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

SUPPORTED_SOURCE_NAMES = {"seed_catalog", "github_trending", "hackernews"}


def run_main_for_test():
    return main()


def main() -> int:
    parser = argparse.ArgumentParser(description="Market-first technology radar pipeline")
    parser.add_argument("--dry-run", action="store_true", help="Run the pipeline without writing public output")
    parser.add_argument("--max-technologies", type=int, help="Maximum technologies to publish")
    parser.add_argument("--sources", type=str, help="Comma-separated list of discovery sources")
    args = parser.parse_args()

    config = load_etl_config(str(Path(__file__).resolve().parent / "config.yaml"))
    if args.max_technologies is not None:
        config.distribution.target_total = max(1, int(args.max_technologies))

    source_names = _parse_sources(args.sources) if args.sources else None
    result = run_pipeline(config=config, source_names=source_names)

    _write_internal_artifacts(result)

    if args.dry_run:
        print(json.dumps(result["public_preview"], indent=2))
        return 0

    publish_radar(result["harmonized"], Path(config.output.public_file))
    return 0


def run_pipeline(config: ETLConfig, source_names: set[str] | None = None) -> dict:
    collector = DiscoveryCollector(build_default_sources(config, source_names=source_names))
    raw_records = collector.collect()
    market_entities = resolve_market_entities(raw_records)
    snapshot = build_market_snapshot(market_entities)
    lane_packs = pack_lanes(snapshot)

    decisions = [
        decide_lane(lane_input, max_items=max(3, config.distribution.target_total // max(1, len(lane_packs))))
        for lane_input in lane_packs.values()
    ]
    bundle = EditorialDecisionBundle(decisions=decisions)
    harmonized = harmonize_decisions(bundle, target_total=config.distribution.target_total)
    harmonized.setdefault("meta", {}).setdefault("pipeline", {})["collected"] = len(raw_records)

    return {
        "raw_records": raw_records,
        "snapshot": [entity.model_dump(mode="json") for entity in snapshot],
        "lane_packs": {lane: pack.model_dump(mode="json") for lane, pack in lane_packs.items()},
        "decisions": bundle.model_dump(mode="json"),
        "harmonized": harmonized,
        "public_preview": publish_radar(harmonized, Path("artifacts/data.ai.preview.json")),
    }


def _parse_sources(value: str) -> set[str]:
    source_names = {item.strip() for item in value.split(",") if item.strip()}
    invalid = sorted(source_names - SUPPORTED_SOURCE_NAMES)
    if invalid or not source_names:
        raise SystemExit(
            "Invalid --sources value. Supported values: " + ",".join(sorted(SUPPORTED_SOURCE_NAMES))
        )
    return source_names


def _write_internal_artifacts(result: dict) -> None:
    artifacts_dir = Path("artifacts")
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    artifact_map = {
        "market-snapshot.json": result["snapshot"],
        "lane-packs.json": result["lane_packs"],
        "editorial-decisions.json": result["decisions"],
        "editorial-harmonized.json": result["harmonized"],
    }
    for filename, payload in artifact_map.items():
        (artifacts_dir / filename).write_text(json.dumps(payload, indent=2) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
