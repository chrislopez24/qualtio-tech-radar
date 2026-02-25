"""Main Pipeline for Tech Radar Data Collection and Processing"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

from etl.pipeline import RadarPipeline
from etl.config import ETLConfig, load_etl_config
from etl.output_generator import sanitize_for_public
from etl.shadow_eval import compare_outputs, write_report, meets_quality_thresholds, DEFAULT_THRESHOLDS


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
    parser.add_argument("--shadow", action="store_true", help="Run in shadow mode with quality evaluation")
    parser.add_argument("--shadow-baseline", type=str, help="Path to baseline output for shadow mode comparison")
    parser.add_argument("--shadow-output", type=str, default="artifacts/shadow_eval.json", help="Path to write shadow eval report")
    parser.add_argument("--shadow-threshold-core-overlap", type=float, default=DEFAULT_THRESHOLDS["core_overlap"], help="Minimum core overlap threshold")
    parser.add_argument("--shadow-threshold-leader-coverage", type=float, default=DEFAULT_THRESHOLDS["leader_coverage"], help="Minimum leader coverage threshold")
    parser.add_argument("--shadow-threshold-watchlist-recall", type=float, default=DEFAULT_THRESHOLDS["watchlist_recall"], help="Minimum watchlist recall threshold")
    parser.add_argument("--shadow-threshold-llm-reduction", type=float, default=DEFAULT_THRESHOLDS["llm_call_reduction"], help="Minimum LLM call reduction threshold")

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

        technologies = result.get("technologies", []) if isinstance(result, dict) else []
        timestamp = datetime.now().isoformat()

        public_output_path = Path(config.output.public_file)
        public_output_path.parent.mkdir(parents=True, exist_ok=True)

        public_output_data = {
            "updatedAt": timestamp,
            "technologies": [sanitize_for_public(tech) for tech in technologies],
        }

        with open(public_output_path, "w") as f:
            json.dump(public_output_data, f, indent=2)

        print(f"\nPublic output saved to: {public_output_path}")

        # Shadow mode: compare against baseline and evaluate quality
        if args.shadow:
            print("\n" + "-" * 60)
            print("Running in SHADOW MODE - Quality Evaluation")
            print("-" * 60)

            if not args.shadow_baseline:
                print("Warning: --shadow-baseline not specified, skipping quality evaluation")
            else:
                baseline_path = Path(args.shadow_baseline)
                if not baseline_path.exists():
                    print(f"Warning: Baseline file not found: {baseline_path}")
                else:
                    with open(baseline_path) as f:
                        baseline = json.load(f)

                    # Compare outputs
                    report = compare_outputs(baseline, public_output_data)

                    # Write report
                    shadow_output_path = Path(args.shadow_output)
                    write_report(report, shadow_output_path)
                    print(f"\nShadow eval report saved to: {shadow_output_path}")

                    # Check thresholds
                    thresholds = {
                        "core_overlap": args.shadow_threshold_core_overlap,
                        "leader_coverage": args.shadow_threshold_leader_coverage,
                        "watchlist_recall": args.shadow_threshold_watchlist_recall,
                        "llm_call_reduction": args.shadow_threshold_llm_reduction,
                    }

                    print("\nQuality Metrics:")
                    print(f"  Core Overlap:      {report['core_overlap']:.2%} (threshold: {thresholds['core_overlap']:.0%})")
                    print(f"  Leader Coverage:   {report['leader_coverage']:.2%} (threshold: {thresholds['leader_coverage']:.0%})")
                    print(f"  Watchlist Recall:  {report['watchlist_recall']:.2%} (threshold: {thresholds['watchlist_recall']:.0%})")
                    print(f"  LLM Reduction:     {report['llm_call_reduction']:.2%} (threshold: {thresholds['llm_call_reduction']:.0%})")

                    if meets_quality_thresholds(report, thresholds):
                        print("\n✓ All quality thresholds met - GO for rollout")
                    else:
                        print("\n✗ Quality thresholds not met - NO-GO for rollout")
                        return 1

        print("\n" + "=" * 60)
        print("Pipeline completed successfully!")
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main() if hasattr(main, "__code__") and main.__code__.co_argcount == 0 else main())
