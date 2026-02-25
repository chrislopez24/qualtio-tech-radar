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
