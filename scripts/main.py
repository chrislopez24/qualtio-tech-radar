"""Main Pipeline for Tech Radar Data Collection and Processing"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from etl.pipeline import RadarPipeline
from etl.config import ETLConfig, load_etl_config


def run_main_for_test():
    """Entry point for testing - returns exit code"""
    return main()


def main():
    """Main entry point with backward-compatible CLI"""
    parser = argparse.ArgumentParser(description="Tech Radar Data Pipeline")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    parser.add_argument("--dry-run", action="store_true", help="Run without making changes")
    parser.add_argument("--max-technologies", type=int, help="Maximum technologies to process")
    parser.add_argument("--sources", type=str, help="Comma-separated list of sources (github_trending,hackernews,google_trends)")

    args = parser.parse_args()

    try:
        config = load_etl_config("scripts/config.yaml")

        if args.max_technologies:
            config.deep_scan.repos = args.max_technologies * [""][:1] or []

        if args.sources:
            source_names = [s.strip() for s in args.sources.split(",")]
            config.sources.github_trending.enabled = "github_trending" in source_names
            config.sources.hackernews.enabled = "hackernews" in source_names
            config.sources.google_trends.enabled = "google_trends" in source_names

        if args.dry_run:
            print("[DRY RUN] Pipeline execution simulated (no data will be collected)")
            return 0

        pipeline = RadarPipeline(
            config=config,
            checkpoint_path=".checkpoint/radar.json",
            save_interval=config.checkpoint.interval,
            resume=args.resume,
        )

        result = pipeline.run()

        output_path = config.output.public_file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        output_data = {
            "updatedAt": datetime.now().isoformat(),
            "technologies": result.get("technologies", []) if isinstance(result, dict) else []
        }

        with open(output_file, "w") as f:
            json.dump(output_data, f, indent=2)

        print(f"\nOutput saved to: {output_path}")
        print("\n" + "=" * 60)
        print("Pipeline completed successfully!")
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main() if hasattr(main, "__code__") and main.__code__.co_argcount == 0 else main())