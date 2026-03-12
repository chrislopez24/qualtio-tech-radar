"""Market-first radar pipeline entrypoint."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from dotenv import load_dotenv

from etl.config import load_etl_config
from etl.publish.publisher import publish_radar
from etl.runner import run_market_radar_pipeline, write_internal_artifacts

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
    result = run_market_radar_pipeline(config=config, source_names=source_names)

    write_internal_artifacts(result)

    if args.dry_run:
        print(json.dumps(result["public_preview"], indent=2))
        return 0

    publish_radar(result["harmonized"], Path(config.output.public_file))
    return 0


def _parse_sources(value: str) -> set[str]:
    source_names = {item.strip() for item in value.split(",") if item.strip()}
    invalid = sorted(source_names - SUPPORTED_SOURCE_NAMES)
    if invalid or not source_names:
        raise SystemExit(
            "Invalid --sources value. Supported values: " + ",".join(sorted(SUPPORTED_SOURCE_NAMES))
        )
    return source_names


if __name__ == "__main__":
    raise SystemExit(main())
