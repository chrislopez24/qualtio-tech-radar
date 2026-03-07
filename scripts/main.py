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
from etl.checkpoint import safe_json_write
from etl.output_generator import sanitize_for_public
from etl.shadow_eval import (
    compare_outputs,
    write_report,
    build_shadow_eval_report,
    classify_quality_gate,
    update_leader_stability_state,
    select_top_leaders,
    deserialize_leader_state,
    serialize_leader_state,
    DEFAULT_THRESHOLDS,
)

SUPPORTED_SOURCE_NAMES = {
    "github_trending",
    "hackernews",
    "deps_dev",
    "pypistats",
    "osv",
}


def run_main_for_test():
    """Entry point for testing - returns exit code"""
    return main()


def main():
    """Main entry point with backward-compatible CLI"""
    parser = argparse.ArgumentParser(description="Tech Radar Data Pipeline")
    parser.add_argument("--resume", action="store_true", help="Resume from checkpoint")
    parser.add_argument("--dry-run", action="store_true", help="Run without making changes")
    parser.add_argument("--max-technologies", type=int, help="Maximum technologies to include in radar output")
    parser.add_argument("--sources", type=str, help="Comma-separated list of sources (github_trending,hackernews)")
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
        config = load_etl_config(str(Path(__file__).parent / "config.yaml"))
        public_output_path = Path(config.output.public_file)

        def build_shadow_summary(
            report: dict[str, object] | None,
            status: str,
            leader_state: dict[str, object] | None = None,
        ) -> dict[str, object]:
            source = report or {}
            raw_candidate_changes = source.get("candidate_changes")
            candidate_changes = raw_candidate_changes if isinstance(raw_candidate_changes, dict) else {}

            normalized_candidate_changes = {}
            for key in sorted(candidate_changes.keys()):
                value = candidate_changes.get(key)
                if not isinstance(value, dict):
                    continue
                change_type = value.get("change_type")
                normalized_candidate_changes[str(key)] = {
                    "leaderId": str(value.get("leader_id", "")),
                    "changeType": change_type if change_type in {"added", "removed"} else "added",
                    "consecutiveCount": int(value.get("consecutive_count", 0)),
                }

            raw_transition_summary = source.get("leader_transition_summary")
            transition_summary = raw_transition_summary if isinstance(raw_transition_summary, dict) else {}

            return {
                "status": status,
                "coreOverlap": source.get("core_overlap"),
                "leaderCoverage": source.get("leader_coverage"),
                "watchlistRecall": source.get("watchlist_recall"),
                "llmCallReduction": source.get("llm_call_reduction"),
                "filteredCount": source.get("filtered_count", 0),
                "addedCount": source.get("added_count", 0),
                "filteredByRing": source.get("filtered_by_ring", {}),
                "filteredSample": source.get("filtered_sample", []),
                "nextAction": source.get("next_action"),
                "leaderTransitionSummary": {
                    "candidateCount": int(transition_summary.get("candidate_count", 0)),
                    "promotedCount": int(transition_summary.get("promoted_count", 0)),
                },
                "leaderState": serialize_leader_state(leader_state) if leader_state is not None else {},
                "candidateChanges": normalized_candidate_changes,
            }

        def extract_observed_leaders(payload: dict) -> set[str]:
            technologies = payload.get("technologies", [])
            return select_top_leaders(technologies)

        def run_shadow_evaluation(
            baseline_path: Path,
            current_payload: dict,
            output_path: Path,
        ) -> tuple[int, dict[str, object]]:
            if not baseline_path.exists():
                print(f"Warning: Baseline file not found: {baseline_path}")
                return 0, build_shadow_summary(report=None, status="skip")

            with open(baseline_path) as f:
                baseline = json.load(f)

            report = compare_outputs(baseline, current_payload)

            thresholds = {
                "core_overlap": args.shadow_threshold_core_overlap,
                "leader_coverage": args.shadow_threshold_leader_coverage,
                "watchlist_recall": args.shadow_threshold_watchlist_recall,
                "llm_call_reduction": args.shadow_threshold_llm_reduction,
            }

            previous_shadow_state_raw = baseline.get("meta", {}).get("shadowGate", {}).get("leaderState", {})
            previous_shadow_state = deserialize_leader_state(previous_shadow_state_raw)
            observed_leaders = extract_observed_leaders(current_payload)
            next_leader_state = update_leader_stability_state(
                previous_state=previous_shadow_state,
                observed_leaders=observed_leaders,
                run_id=datetime.now().isoformat(),
            )

            report = build_shadow_eval_report(report, thresholds, leader_state=next_leader_state)
            gate = classify_quality_gate(report, thresholds, leader_state=next_leader_state)

            write_report(report, output_path)
            print(f"\nShadow eval report saved to: {output_path}")

            print("\nQuality Metrics:")
            print(f"  Core Overlap:      {report['core_overlap']:.2%} (threshold: {thresholds['core_overlap']:.0%})")
            print(f"  Leader Coverage:   {report['leader_coverage']:.2%} (threshold: {thresholds['leader_coverage']:.0%})")
            print(f"  Watchlist Recall:  {report['watchlist_recall']:.2%} (threshold: {thresholds['watchlist_recall']:.0%})")
            print(f"  LLM Reduction:     {report['llm_call_reduction']:.2%} (threshold: {thresholds['llm_call_reduction']:.0%})")
            print(f"  Filtered by gate:  {report.get('filtered_count', 0)}")
            print(f"  Gate status:       {report.get('gate_status', 'unknown').upper()}")

            status = gate["status"]
            if status == "pass":
                print("\n✓ All quality thresholds met - GO for rollout")
                return 0, build_shadow_summary(report, "pass", leader_state=next_leader_state)
            if status == "warn":
                print("\n⚠ Quality thresholds met but leader changes are not yet stable")
                return 0, build_shadow_summary(report, "warn", leader_state=next_leader_state)

            print("\n✗ Quality thresholds not met - NO-GO for rollout")
            return 1, build_shadow_summary(report, "fail", leader_state=previous_shadow_state)

        if args.max_technologies is not None:
            target_total = max(1, int(args.max_technologies))
            config.distribution.target_total = target_total
            config.distribution.min_per_quadrant = 1
            config.distribution.max_per_quadrant = min(config.distribution.max_per_quadrant, target_total)

        if args.sources:
            source_names = {s.strip() for s in args.sources.split(",") if s.strip()}
            invalid_sources = sorted(source_names - SUPPORTED_SOURCE_NAMES)
            if invalid_sources or not source_names:
                print(
                    "Invalid --sources value. Supported values: "
                    + ",".join(sorted(SUPPORTED_SOURCE_NAMES))
                )
                return 1

            config.sources.github_trending.enabled = "github_trending" in source_names
            config.sources.hackernews.enabled = "hackernews" in source_names
            config.sources.deps_dev.enabled = "deps_dev" in source_names
            config.sources.pypistats.enabled = "pypistats" in source_names
            config.sources.osv.enabled = "osv" in source_names

        if args.dry_run:
            print("[DRY RUN] Pipeline execution simulated (no data will be collected)")
            return 0

        if args.shadow_only:
            print("\n" + "-" * 60)
            print("Running in SHADOW-ONLY MODE")
            print("-" * 60)

            current_path = Path(args.shadow_current) if args.shadow_current else public_output_path
            baseline_arg = Path(args.shadow_baseline) if args.shadow_baseline else None
            if baseline_arg is None:
                print("Warning: --shadow-baseline not specified, skipping quality evaluation")
                if not current_path.exists():
                    print(f"Error: Current output file not found: {current_path}")
                    return 1
                with open(current_path) as f:
                    current_payload = json.load(f)
                current_payload.setdefault("meta", {})["shadowGate"] = build_shadow_summary(report=None, status="skip")
                safe_json_write(current_path, current_payload)
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
            safe_json_write(current_path, current_payload)

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

        safe_json_write(public_output_path, public_output_data)

        print(f"\nPublic output saved to: {public_output_path}")

        # Shadow mode: compare against baseline and evaluate quality
        if args.shadow:
            print("\n" + "-" * 60)
            print("Running in SHADOW MODE - Quality Evaluation")
            print("-" * 60)

            if not args.shadow_baseline:
                print("Warning: --shadow-baseline not specified, skipping quality evaluation")
                public_output_data.setdefault("meta", {})["shadowGate"] = build_shadow_summary(report=None, status="skip")
                safe_json_write(public_output_path, public_output_data)
            else:
                exit_code, shadow_summary = run_shadow_evaluation(
                    baseline_path=Path(args.shadow_baseline),
                    current_payload=public_output_data,
                    output_path=Path(args.shadow_output),
                )
                public_output_data.setdefault("meta", {})["shadowGate"] = shadow_summary

                safe_json_write(public_output_path, public_output_data)

                if exit_code != 0:
                    return exit_code

        print("\n" + "=" * 60)
        print("Pipeline completed successfully!")
        print("=" * 60)

        return 0

    except Exception as e:
        print(f"\nError: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
