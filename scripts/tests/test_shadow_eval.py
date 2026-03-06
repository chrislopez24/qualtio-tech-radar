"""Tests for shadow quality evaluator"""

import pytest
import json
from pathlib import Path


def test_shadow_eval_computes_quality_contract():
    """Shadow evaluator should compute quality metrics comparing baseline and optimized outputs"""
    from etl.shadow_eval import compare_outputs

    baseline = {"technologies": [{"id": "react"}, {"id": "kubernetes"}]}
    optimized = {"technologies": [{"id": "react"}, {"id": "kubernetes"}]}

    report = compare_outputs(baseline, optimized)
    assert report["core_overlap"] == 1.0


def test_shadow_eval_computes_leader_coverage():
    """Shadow evaluator should compute leader coverage metric"""
    from etl.shadow_eval import compare_outputs

    baseline = {
        "technologies": [
            {"id": "react", "ring": "adopt"},
            {"id": "kubernetes", "ring": "adopt"},
            {"id": "new-tool", "ring": "assess"},
        ]
    }
    optimized = {
        "technologies": [
            {"id": "react", "ring": "adopt"},
            {"id": "kubernetes", "ring": "adopt"},
        ]
    }

    report = compare_outputs(baseline, optimized)
    assert "leader_coverage" in report
    assert 0.0 <= report["leader_coverage"] <= 1.0


def test_shadow_eval_leader_coverage_uses_leader_ids_not_ring_labels_only():
    """Leader coverage should stay high when leader IDs are preserved even if ring labels change."""
    from etl.shadow_eval import compare_outputs

    baseline = {
        "technologies": [
            {"id": "react", "ring": "adopt", "marketScore": 98},
            {"id": "kubernetes", "ring": "adopt", "marketScore": 97},
            {"id": "bun", "ring": "assess", "marketScore": 80},
        ]
    }
    optimized = {
        "technologies": [
            {"id": "react", "ring": "trial", "marketScore": 98},
            {"id": "kubernetes", "ring": "trial", "marketScore": 97},
            {"id": "bun", "ring": "assess", "marketScore": 80},
        ]
    }

    report = compare_outputs(baseline, optimized)
    assert report["leader_coverage"] == 1.0


def test_shadow_eval_computes_watchlist_recall():
    """Shadow evaluator should compute watchlist recall metric"""
    from etl.shadow_eval import compare_outputs

    baseline = {
        "technologies": [
            {"id": "react", "ring": "adopt"},
            {"id": "trending-tool", "ring": "trial", "trend": "up"},
        ]
    }
    optimized = {
        "technologies": [
            {"id": "react", "ring": "adopt"},
            {"id": "trending-tool", "ring": "trial", "trend": "up"},
        ]
    }

    report = compare_outputs(baseline, optimized)
    assert "watchlist_recall" in report
    assert 0.0 <= report["watchlist_recall"] <= 1.0


def test_shadow_eval_computes_llm_call_reduction():
    """Shadow evaluator should compute LLM call reduction percentage"""
    from etl.shadow_eval import compare_outputs

    baseline = {"technologies": [{"id": "react"}], "metadata": {"llm_calls": 100}}
    optimized = {"technologies": [{"id": "react"}], "metadata": {"llm_calls": 30}}

    report = compare_outputs(baseline, optimized)
    assert "llm_call_reduction" in report
    assert report["llm_call_reduction"] == 0.7  # 70% reduction


def test_shadow_eval_handles_missing_technologies():
    """Shadow evaluator should handle cases where optimized is missing technologies from baseline"""
    from etl.shadow_eval import compare_outputs

    baseline = {"technologies": [{"id": "react"}, {"id": "kubernetes"}, {"id": "docker"}]}
    optimized = {"technologies": [{"id": "react"}, {"id": "kubernetes"}]}

    report = compare_outputs(baseline, optimized)
    assert report["core_overlap"] < 1.0


def test_shadow_eval_handles_empty_outputs():
    """Shadow evaluator should handle empty outputs gracefully"""
    from etl.shadow_eval import compare_outputs

    baseline = {"technologies": []}
    optimized = {"technologies": []}

    report = compare_outputs(baseline, optimized)
    assert report["core_overlap"] == 1.0


def test_shadow_eval_writes_report_to_file(tmp_path):
    """Shadow evaluator should write report to JSON file"""
    from etl.shadow_eval import compare_outputs, write_report

    baseline = {"technologies": [{"id": "react"}]}
    optimized = {"technologies": [{"id": "react"}]}

    report = compare_outputs(baseline, optimized)
    output_path = tmp_path / "shadow_eval.json"
    write_report(report, output_path)

    assert output_path.exists()
    with open(output_path) as f:
        loaded = json.load(f)
    assert loaded["core_overlap"] == 1.0


def test_shadow_eval_core_overlap_is_baseline_coverage_when_optimized_has_more_items():
    """Core overlap should stay high when optimized keeps all baseline IDs and adds new ones."""
    from etl.shadow_eval import compare_outputs

    baseline = {"technologies": [{"id": "react"}, {"id": "kubernetes"}]}
    optimized = {"technologies": [{"id": "react"}, {"id": "kubernetes"}, {"id": "bun"}]}

    report = compare_outputs(baseline, optimized)
    assert report["core_overlap"] == 1.0


def test_shadow_eval_reports_filtered_counts_and_watchlist_usage():
    """Shadow evaluator should expose filtered counts and respect explicit watchlist."""
    from etl.shadow_eval import compare_outputs

    baseline = {
        "technologies": [{"id": "react", "ring": "adopt"}, {"id": "bun", "ring": "assess"}],
        "watchlist": [{"id": "bun"}],
    }
    optimized = {
        "technologies": [{"id": "react", "ring": "adopt"}],
        "watchlist": [],
    }

    report = compare_outputs(baseline, optimized)
    assert report["filtered_count"] == 1
    assert report["filtered_by_ring"].get("assess") == 1
    assert report["watchlist_recall"] == 0.0


def test_shadow_eval_ignores_resource_like_repos_in_overlap_and_watchlist_metrics():
    from etl.shadow_eval import compare_outputs

    baseline = {
        "technologies": [
            {"id": "react", "name": "React", "ring": "adopt"},
            {"id": "free-programming-books", "name": "free-programming-books", "ring": "trial"},
        ],
        "watchlist": [
            {"id": "next.js", "name": "Next.js"},
            {"id": "free-programming-books", "name": "free-programming-books"},
        ],
    }
    optimized = {
        "technologies": [
            {"id": "react", "name": "React", "ring": "adopt"},
        ],
        "watchlist": [
            {"id": "next.js", "name": "Next.js"},
        ],
    }

    report = compare_outputs(baseline, optimized)

    assert report["core_overlap"] == 1.0
    assert report["watchlist_recall"] == 1.0
    assert report["filtered_count"] == 0


def test_shadow_eval_falls_back_to_pipeline_meta_llm_counts():
    from etl.shadow_eval import compare_outputs

    baseline = {
        "technologies": [{"id": "react"}],
        "meta": {"pipeline": {"classified": 10}},
    }
    optimized = {
        "technologies": [{"id": "react"}],
        "meta": {"pipeline": {"llmCalls": 4}},
    }

    report = compare_outputs(baseline, optimized)
    assert report["llm_call_reduction"] == 0.6


def test_shadow_eval_uses_classified_as_baseline_floor_when_present():
    from etl.shadow_eval import compare_outputs

    baseline = {
        "technologies": [{"id": "react"}],
        "meta": {"pipeline": {"classified": 20, "llmCalls": 7}},
    }
    optimized = {
        "technologies": [{"id": "react"}],
        "meta": {"pipeline": {"llmCalls": 7}},
    }

    report = compare_outputs(baseline, optimized)
    assert report["llm_call_reduction"] == 0.65


def test_leader_stability_bootstraps_stable_set_from_first_run():
    from etl.shadow_eval import update_leader_stability_state

    state = update_leader_stability_state(
        previous_state=None,
        observed_leaders={"react", "kubernetes"},
        run_id="run-1",
    )

    assert set(state["stable_leaders"]) == {"react", "kubernetes"}
    assert state["candidate_changes"] == {}
    assert state["promoted_changes"] == []


def test_leader_stability_tracks_new_candidate_with_count_one():
    from etl.shadow_eval import update_leader_stability_state

    previous_state = {
        "stable_leaders": ["react", "kubernetes"],
        "candidate_changes": {},
    }

    state = update_leader_stability_state(
        previous_state=previous_state,
        observed_leaders={"react", "kubernetes", "bun"},
        run_id="run-2",
    )

    candidate = state["candidate_changes"]["bun:added"]
    assert candidate["consecutive_count"] == 1
    assert candidate["first_seen_run"] == "run-2"
    assert candidate["last_seen_run"] == "run-2"
    assert "bun" not in state["stable_leaders"]


def test_leader_stability_increments_count_for_consecutive_change():
    from etl.shadow_eval import update_leader_stability_state

    previous_state = {
        "stable_leaders": ["react", "kubernetes"],
        "candidate_changes": {
            "bun:added": {
                "leader_id": "bun",
                "change_type": "added",
                "consecutive_count": 1,
                "first_seen_run": "run-2",
                "last_seen_run": "run-2",
            }
        },
    }

    state = update_leader_stability_state(
        previous_state=previous_state,
        observed_leaders={"react", "kubernetes", "bun"},
        run_id="run-3",
    )

    assert state["candidate_changes"]["bun:added"]["consecutive_count"] == 2
    assert "bun" not in state["stable_leaders"]


def test_leader_stability_resets_interrupted_candidate_changes():
    from etl.shadow_eval import update_leader_stability_state

    previous_state = {
        "stable_leaders": ["react", "kubernetes"],
        "candidate_changes": {
            "bun:added": {
                "leader_id": "bun",
                "change_type": "added",
                "consecutive_count": 2,
                "first_seen_run": "run-2",
                "last_seen_run": "run-3",
            }
        },
    }

    state = update_leader_stability_state(
        previous_state=previous_state,
        observed_leaders={"react", "kubernetes"},
        run_id="run-4",
    )

    assert state["candidate_changes"] == {}
    assert set(state["stable_leaders"]) == {"react", "kubernetes"}


def test_leader_stability_promotes_change_after_three_consecutive_runs():
    from etl.shadow_eval import update_leader_stability_state

    state_run_2 = {
        "stable_leaders": ["react", "kubernetes"],
        "candidate_changes": {
            "bun:added": {
                "leader_id": "bun",
                "change_type": "added",
                "consecutive_count": 1,
                "first_seen_run": "run-2",
                "last_seen_run": "run-2",
            }
        },
    }

    state_run_3 = update_leader_stability_state(
        previous_state=state_run_2,
        observed_leaders={"react", "kubernetes", "bun"},
        run_id="run-3",
    )

    state_run_4 = update_leader_stability_state(
        previous_state=state_run_3,
        observed_leaders={"react", "kubernetes", "bun"},
        run_id="run-4",
    )

    assert set(state_run_4["stable_leaders"]) == {"react", "kubernetes", "bun"}
    assert state_run_4["candidate_changes"] == {}
    assert {"leader_id": "bun", "change_type": "added"} in state_run_4["promoted_changes"]


def test_quality_gate_classifies_as_pass_when_thresholds_met_and_no_candidates():
    from etl.shadow_eval import classify_quality_gate

    report = {
        "core_overlap": 0.95,
        "leader_coverage": 1.0,
        "watchlist_recall": 1.0,
        "llm_call_reduction": 0.8,
    }
    thresholds = {
        "core_overlap": 0.85,
        "leader_coverage": 0.95,
        "watchlist_recall": 0.80,
        "llm_call_reduction": 0.6,
    }

    gate = classify_quality_gate(report, thresholds, leader_state={"candidate_changes": {}})
    assert gate["status"] == "pass"
    assert gate["next_action"] == "rollout-approved"
    assert gate["next_action_message"] == "Quality checks passed and rollout is approved."
    assert gate["next_action_code"] == "rollout-approved"


def test_quality_gate_classifies_as_warn_when_candidate_changes_exist():
    from etl.shadow_eval import classify_quality_gate

    report = {
        "core_overlap": 0.95,
        "leader_coverage": 1.0,
        "watchlist_recall": 1.0,
        "llm_call_reduction": 0.8,
    }
    thresholds = {
        "core_overlap": 0.85,
        "leader_coverage": 0.95,
        "watchlist_recall": 0.80,
        "llm_call_reduction": 0.6,
    }
    leader_state = {
        "candidate_changes": {
            "bun:added": {
                "leader_id": "bun",
                "change_type": "added",
                "consecutive_count": 2,
            }
        },
        "promoted_changes": [],
    }

    gate = classify_quality_gate(report, thresholds, leader_state=leader_state)
    assert gate["status"] == "warn"
    assert gate["next_action"] == "await-stable-leader-transition"
    assert gate["next_action_message"] == "Await stable leader transition before rollout approval."
    assert gate["next_action_code"] == "await-stable-leader-transition"


def test_quality_gate_classifies_as_fail_when_any_threshold_breaches():
    from etl.shadow_eval import classify_quality_gate

    report = {
        "core_overlap": 0.95,
        "leader_coverage": 0.6,
        "watchlist_recall": 1.0,
        "llm_call_reduction": 0.8,
    }
    thresholds = {
        "core_overlap": 0.85,
        "leader_coverage": 0.95,
        "watchlist_recall": 0.80,
        "llm_call_reduction": 0.6,
    }

    gate = classify_quality_gate(report, thresholds, leader_state={"candidate_changes": {}})
    assert gate["status"] == "fail"
    assert gate["next_action"] == "investigate-quality-regression"
    assert gate["next_action_message"] == "Investigate quality regression before rollout."
    assert gate["next_action_code"] == "investigate-quality-regression"
    assert "leader_coverage" in gate["failed_metrics"]


def test_build_shadow_eval_report_includes_gate_and_leader_state_fields():
    from etl.shadow_eval import build_shadow_eval_report

    metrics = {
        "core_overlap": 0.95,
        "leader_coverage": 1.0,
        "watchlist_recall": 1.0,
        "llm_call_reduction": 0.8,
    }
    thresholds = {
        "core_overlap": 0.85,
        "leader_coverage": 0.95,
        "watchlist_recall": 0.80,
        "llm_call_reduction": 0.6,
    }
    leader_state = {
        "stable_leaders": ["react", "kubernetes"],
        "candidate_changes": {},
        "promoted_changes": [],
    }

    report = build_shadow_eval_report(metrics, thresholds, leader_state=leader_state)

    assert report["gate_status"] == "pass"
    assert report["stable_leaders"] == ["react", "kubernetes"]
    assert "leader_transition_summary" in report


def test_build_shadow_eval_report_includes_leader_transition_explainability_details():
    from etl.shadow_eval import build_shadow_eval_report

    metrics = {
        "core_overlap": 0.95,
        "leader_coverage": 1.0,
        "watchlist_recall": 1.0,
        "llm_call_reduction": 0.8,
    }
    thresholds = {
        "core_overlap": 0.85,
        "leader_coverage": 0.95,
        "watchlist_recall": 0.80,
        "llm_call_reduction": 0.6,
    }
    leader_state = {
        "stable_leaders": ["react", "kubernetes"],
        "candidate_changes": {
            "bun:added": {
                "leader_id": "bun",
                "change_type": "added",
                "consecutive_count": 2,
            }
        },
        "promoted_changes": [{"leader_id": "terraform", "change_type": "removed"}],
    }

    report = build_shadow_eval_report(metrics, thresholds, leader_state=leader_state)

    assert report["leader_transition_summary"] == {
        "candidate_count": 1,
        "promoted_count": 1,
    }
    assert report["candidate_changes"]["bun:added"] == {
        "leader_id": "bun",
        "change_type": "added",
        "consecutive_count": 2,
    }


def test_build_shadow_eval_report_includes_human_readable_next_action():
    from etl.shadow_eval import build_shadow_eval_report

    metrics = {
        "core_overlap": 0.95,
        "leader_coverage": 1.0,
        "watchlist_recall": 1.0,
        "llm_call_reduction": 0.8,
    }
    thresholds = {
        "core_overlap": 0.85,
        "leader_coverage": 0.95,
        "watchlist_recall": 0.80,
        "llm_call_reduction": 0.6,
    }
    leader_state = {
        "stable_leaders": ["react", "kubernetes"],
        "candidate_changes": {
            "bun:added": {
                "leader_id": "bun",
                "change_type": "added",
                "consecutive_count": 2,
            }
        },
        "promoted_changes": [],
    }

    report = build_shadow_eval_report(metrics, thresholds, leader_state=leader_state)

    assert report["next_action"] == "await-stable-leader-transition"
    assert report["next_action_message"] == "Await stable leader transition before rollout approval."
    assert report["next_action_code"] == "await-stable-leader-transition"


def test_deserialize_leader_state_normalizes_meta_shape_and_sorts_keys():
    from etl.shadow_eval import deserialize_leader_state

    raw_state = {
        "stableLeaders": ["react", "bun", "kubernetes"],
        "candidateChanges": {
            "react:removed": {
                "leaderId": "react",
                "changeType": "removed",
                "consecutiveCount": 1,
                "firstSeenRun": "run-4",
                "lastSeenRun": "run-4",
            },
            "bun:added": {
                "leaderId": "bun",
                "changeType": "added",
                "consecutiveCount": 2,
                "firstSeenRun": "run-3",
                "lastSeenRun": "run-4",
            },
        },
        "promotedChanges": [{"leaderId": "terraform", "changeType": "added"}],
        "lastRunId": "run-4",
        "promotionRuns": 3,
    }

    state = deserialize_leader_state(raw_state)

    assert state["stable_leaders"] == ["bun", "kubernetes", "react"]
    assert list(state["candidate_changes"].keys()) == ["bun:added", "react:removed"]
    assert state["promoted_changes"] == [{"leader_id": "terraform", "change_type": "added"}]
    assert state["last_run_id"] == "run-4"
    assert state["promotion_runs"] == 3


def test_serialize_leader_state_emits_deterministic_meta_shape():
    from etl.shadow_eval import serialize_leader_state

    state = {
        "stable_leaders": ["react", "bun", "kubernetes"],
        "candidate_changes": {
            "react:removed": {
                "leader_id": "react",
                "change_type": "removed",
                "consecutive_count": 1,
                "first_seen_run": "run-4",
                "last_seen_run": "run-4",
            },
            "bun:added": {
                "leader_id": "bun",
                "change_type": "added",
                "consecutive_count": 2,
                "first_seen_run": "run-3",
                "last_seen_run": "run-4",
            },
        },
        "promoted_changes": [{"leader_id": "terraform", "change_type": "added"}],
        "last_run_id": "run-4",
        "promotion_runs": 3,
    }

    serialized = serialize_leader_state(state)

    assert serialized["stableLeaders"] == ["bun", "kubernetes", "react"]
    assert list(serialized["candidateChanges"].keys()) == ["bun:added", "react:removed"]
    assert serialized["candidateChanges"]["bun:added"] == {
        "leaderId": "bun",
        "changeType": "added",
        "consecutiveCount": 2,
        "firstSeenRun": "run-3",
        "lastSeenRun": "run-4",
    }
    assert serialized["promotedChanges"] == [{"leaderId": "terraform", "changeType": "added"}]
    assert serialized["lastRunId"] == "run-4"
    assert serialized["promotionRuns"] == 3


def test_deserialize_leader_state_handles_non_dict_input_safely():
    from etl.shadow_eval import deserialize_leader_state

    assert deserialize_leader_state("invalid") == {
        "stable_leaders": [],
        "candidate_changes": {},
        "promoted_changes": [],
        "last_run_id": "",
        "promotion_runs": 3,
    }
    assert deserialize_leader_state(["invalid"]) == {
        "stable_leaders": [],
        "candidate_changes": {},
        "promoted_changes": [],
        "last_run_id": "",
        "promotion_runs": 3,
    }


def test_shadow_eval_clamps_llm_call_reduction_when_optimized_exceeds_baseline():
    from etl.shadow_eval import compare_outputs

    baseline = {"technologies": [{"id": "react"}], "metadata": {"llm_calls": 10}}
    optimized = {"technologies": [{"id": "react"}], "metadata": {"llm_calls": 20}}

    report = compare_outputs(baseline, optimized)
    assert report["llm_call_reduction"] == 0.0


def test_extract_metric_inputs_computes_id_sets_and_diffs():
    from etl.shadow_eval import _extract_metric_inputs

    baseline = {
        "technologies": [{"id": "react"}, {"id": "kubernetes"}],
        "watchlist": [{"id": "bun"}],
    }
    optimized = {
        "technologies": [{"id": "react"}, {"id": "bun"}],
        "watchlist": [],
    }

    inputs = _extract_metric_inputs(baseline, optimized)

    assert inputs["baseline_ids"] == {"react", "kubernetes"}
    assert inputs["optimized_ids"] == {"react", "bun"}
    assert inputs["missing_from_optimized"] == ["kubernetes"]
    assert inputs["added_in_optimized"] == ["bun"]


def test_apply_leader_policy_promotes_added_and_removed_candidates():
    from etl.shadow_eval import _apply_leader_policy

    prev_stable = {"react", "kubernetes"}
    next_candidates = {
        "bun:added": {
            "leader_id": "bun",
            "change_type": "added",
            "consecutive_count": 3,
            "first_seen_run": "run-2",
            "last_seen_run": "run-4",
        },
        "kubernetes:removed": {
            "leader_id": "kubernetes",
            "change_type": "removed",
            "consecutive_count": 3,
            "first_seen_run": "run-2",
            "last_seen_run": "run-4",
        },
        "terraform:added": {
            "leader_id": "terraform",
            "change_type": "added",
            "consecutive_count": 2,
            "first_seen_run": "run-3",
            "last_seen_run": "run-4",
        },
    }

    policy = _apply_leader_policy(prev_stable, next_candidates, promotion_runs=3)

    assert policy["stable_leaders"] == ["bun", "react"]
    assert policy["promoted_changes"] == [
        {"leader_id": "bun", "change_type": "added"},
        {"leader_id": "kubernetes", "change_type": "removed"},
    ]
    assert list(policy["remaining_candidates"].keys()) == ["terraform:added"]


def test_collect_failed_metrics_reports_only_breaching_thresholds():
    from etl.shadow_eval import _collect_failed_metrics

    report = {
        "core_overlap": 0.9,
        "leader_coverage": 0.7,
        "watchlist_recall": 1.0,
    }
    thresholds = {
        "core_overlap": 0.85,
        "leader_coverage": 0.95,
        "watchlist_recall": 0.8,
    }

    failed = _collect_failed_metrics(report, thresholds)

    assert failed == {
        "leader_coverage": {
            "required": 0.95,
            "actual": 0.7,
        }
    }
