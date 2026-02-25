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
    parser.add_argument("--shadow-only", action="store_true", help="Run only shadow evaluation using existing output files")
    parser.add_argument("--shadow-baseline", type=str, help="Path to baseline output for shadow mode comparison")
    parser.add_argument("--shadow-current", type=str, help="Path to current output for shadow-only mode")
    parser.add_argument("--shadow-output", type=str, default="artifacts/shadow_eval.json", help="Path to write shadow eval report")
    parser.add_argument("--shadow-threshold-core-overlap", type=float, default=DEFAULT_THRESHOLDS["core_overlap"], help="Minimum core overlap threshold")
    parser.add_argument("--shadow-threshold-leader-coverage", type=float, default=DEFAULT_THRESHOLDS["leader_coverage"], help="Minimum leader coverage threshold")
    parser.add_argument("--shadow-threshold-watchlist-recall", type=float, default=DEFAULT_THRESHOLDS["watchlist_recall"], help="Minimum watchlist recall threshold")
    parser.add_argument("--shadow-threshold-llm-reduction", type=float, default=DEFAULT_THRESHOLDS["llm_call_reduction"], help="Minimum LLM call reduction threshold")

    args = parser.parse_args()

    if args.shadow and args.shadow_only:
        print("Error: --shadow and --shadow-only are mutually exclusive")
        return 1

    try:
        config = load_etl_config("scripts/config.yaml")
        public_output_path = Path(config.output.public_file)

        def build_shadow_summary(report: dict[str, float], status: str) -> dict[str, object]:
            return {
                "status": status,
                "coreOverlap": report.get("core_overlap"),
                "leaderCoverage": report.get("leader_coverage"),
                "watchlistRecall": report.get("watchlist_recall"),
                "llmCallReduction": report.get("llm_call_reduction"),
                "filteredCount": report.get("filtered_count", 0),
                "addedCount": report.get("added_count", 0),
                "filteredByRing": report.get("filtered_by_ring", {}),
                "filteredSample": report.get("filtered_sample", []),
            }

        def run_shadow_evaluation(
            baseline_path: Path,
            current_payload: dict,
            output_path: Path,
        ) -> tuple[int, dict[str, object]]:
            if not baseline_path.exists():
                print(f"Warning: Baseline file not found: {baseline_path}")
                return 0, {"status": "skip"}

            with open(baseline_path) as f:
                baseline = json.load(f)

            report = compare_outputs(baseline, current_payload)
            write_report(report, output_path)
            print(f"\nShadow eval report saved to: {output_path}")

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
            print(f"  Filtered by gate:  {report.get('filtered_count', 0)}")

            passed = meets_quality_thresholds(report, thresholds)
            if passed:
                print("\n✓ All quality thresholds met - GO for rollout")
                return 0, build_shadow_summary(report, "pass")

            print("\n✗ Quality thresholds not met - NO-GO for rollout")
            return 1, build_shadow_summary(report, "fail")

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

        if args.shadow_only:
            print("\n" + "-" * 60)
            print("Running in SHADOW-ONLY MODE")
            print("-" * 60)

            baseline_arg = Path(args.shadow_baseline) if args.shadow_baseline else None
            if baseline_arg is None:
                print("Warning: --shadow-baseline not specified, skipping quality evaluation")
                return 0

            current_path = Path(args.shadow_current) if args.shadow_current else public_output_path
            if not current_path.exists():
                print(f"Error: Current output file not found: {current_path}")
                return 1

            with open(current_path) as f:
                current_payload = json.load(f)

            exit_code, shadow_summary = run_shadow_evaluation(
                baseline_path=baseline_arg,
                current_payload=current_payload,
                output_path=Path(args.shadow_output),
            )

            current_payload.setdefault("meta", {})["shadowGate"] = shadow_summary
            with open(current_path, "w") as f:
                json.dump(current_payload, f, indent=2)

            return exit_code

        pipeline = RadarPipeline(
            config=config,
            checkpoint_path=".checkpoint/radar.json",
            save_interval=config.checkpoint.interval,
            resume=args.resume,
        )

        result = pipeline.run()

        technologies = result.get("technologies", []) if isinstance(result, dict) else []
        watchlist = result.get("watchlist", []) if isinstance(result, dict) else []
        meta = result.get("meta", {}) if isinstance(result, dict) else {}
        timestamp = datetime.now().isoformat()

        public_output_path.parent.mkdir(parents=True, exist_ok=True)

        public_output_data = {
            "updatedAt": timestamp,
            "technologies": [sanitize_for_public(tech) for tech in technologies],
            "watchlist": [sanitize_for_public(tech) for tech in watchlist],
            "meta": meta,
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
                public_output_data.setdefault("meta", {}).setdefault("shadowGate", {"status": "skip"})
            else:
                exit_code, shadow_summary = run_shadow_evaluation(
                    baseline_path=Path(args.shadow_baseline),
                    current_payload=public_output_data,
                    output_path=Path(args.shadow_output),
                )
                public_output_data.setdefault("meta", {})["shadowGate"] = shadow_summary

                with open(public_output_path, "w") as f:
                    json.dump(public_output_data, f, indent=2)

                if exit_code != 0:
                    return exit_code

        print("\n" + "=" * 60)
        print("Pipeline completed successfully!")
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main() if hasattr(main, "__code__") and main.__code__.co_argcount == 0 else main())
