import pytest
import sys
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock


def run_main_for_test():
    from main import main
    with patch("main.RadarPipeline") as mock_pipeline:
        mock_instance = MagicMock()
        mock_instance.run.return_value = {"technologies": [], "updatedAt": "2024-01-01"}
        mock_pipeline.return_value = mock_instance
        
        with patch.object(sys, "argv", ["main.py", "--dry-run"]):
            try:
                result = main()
                return result if result is not None else 0
            except SystemExit as e:
                return e.code
    return 1


def test_main_calls_new_pipeline_and_writes_output(monkeypatch):
    assert run_main_for_test() == 0


def test_main_writes_only_public_output(tmp_path):
    from main import main
    from etl.config import ETLConfig, OutputConfig

    public_file = tmp_path / "data.ai.json"
    internal_file = tmp_path / "data.ai.full.json"

    cfg = ETLConfig(
        output=OutputConfig(
            public_file=str(public_file),
        )
    )

    with patch("main.load_etl_config", return_value=cfg), \
         patch("main.RadarPipeline") as mock_pipeline, \
         patch.object(sys, "argv", ["main.py"]):
        mock_pipeline.return_value.run.return_value = {
            "technologies": [
                {
                    "id": "react",
                    "name": "React",
                    "quadrant": "tools",
                    "ring": "adopt",
                    "description": "UI library",
                    "repoNames": ["facebook/react"],
                }
            ]
        }

        exit_code = main()

    assert exit_code == 0
    assert public_file.exists()
    assert not internal_file.exists()

    public_payload = json.loads(public_file.read_text())

    assert "repoNames" not in public_payload["technologies"][0]


def test_shadow_only_mode_uses_existing_files_without_running_pipeline(tmp_path):
    from main import main
    from etl.config import ETLConfig, OutputConfig

    current_file = tmp_path / "data.ai.json"
    baseline_file = tmp_path / "baseline.json"
    report_file = tmp_path / "shadow_eval.json"

    current_file.write_text(json.dumps({"technologies": [{"id": "react"}], "watchlist": []}))
    baseline_file.write_text(json.dumps({"technologies": [{"id": "react"}], "watchlist": []}))

    cfg = ETLConfig(output=OutputConfig(public_file=str(current_file)))

    with patch("main.load_etl_config", return_value=cfg), \
         patch("main.RadarPipeline") as mock_pipeline, \
         patch.object(
             sys,
             "argv",
             [
                 "main.py",
                 "--shadow-only",
                 "--shadow-baseline",
                 str(baseline_file),
                 "--shadow-current",
                 str(current_file),
                 "--shadow-output",
                 str(report_file),
                 "--shadow-threshold-core-overlap",
                 "0.8",
                 "--shadow-threshold-leader-coverage",
                 "0.0",
                 "--shadow-threshold-watchlist-recall",
                 "0.0",
                 "--shadow-threshold-llm-reduction",
                 "0.0",
             ],
         ):
        exit_code = main()

    assert exit_code == 0
    mock_pipeline.assert_not_called()
    assert report_file.exists()


def assert_skip_shadow_gate_defaults(shadow_gate):
    assert shadow_gate["status"] == "skip"
    assert "nextAction" in shadow_gate
    assert shadow_gate["nextAction"] is None
    assert "filteredCount" in shadow_gate
    assert shadow_gate["filteredCount"] == 0
    assert "addedCount" in shadow_gate
    assert shadow_gate["addedCount"] == 0
    assert "filteredSample" in shadow_gate
    assert shadow_gate["filteredSample"] == []
    assert "candidateChanges" in shadow_gate
    assert shadow_gate["candidateChanges"] == {}
    assert "leaderState" in shadow_gate
    assert shadow_gate["leaderState"] == {}


def test_shadow_gate_contract_is_stable_when_shadow_eval_skips(tmp_path):
    from main import main
    from etl.config import ETLConfig, OutputConfig

    current_file = tmp_path / "data.ai.json"
    missing_baseline_file = tmp_path / "missing-baseline.json"

    current_file.write_text(
        json.dumps(
            {
                "technologies": [{"id": "react", "name": "React"}],
                "watchlist": [],
                "meta": {},
            }
        )
    )

    cfg = ETLConfig(output=OutputConfig(public_file=str(current_file)))

    with patch("main.load_etl_config", return_value=cfg), \
         patch("main.RadarPipeline") as mock_pipeline, \
         patch.object(
             sys,
             "argv",
             [
                 "main.py",
                 "--shadow-only",
                 "--shadow-baseline",
                 str(missing_baseline_file),
                 "--shadow-current",
                 str(current_file),
             ],
         ):
        exit_code = main()

    assert exit_code == 0
    mock_pipeline.assert_not_called()

    payload = json.loads(current_file.read_text())
    shadow_gate = payload["meta"]["shadowGate"]
    assert_skip_shadow_gate_defaults(shadow_gate)


def test_shadow_mode_without_baseline_uses_stable_shadow_gate_contract(tmp_path):
    from main import main
    from etl.config import ETLConfig, OutputConfig

    public_file = tmp_path / "data.ai.json"
    cfg = ETLConfig(output=OutputConfig(public_file=str(public_file)))

    with patch("main.load_etl_config", return_value=cfg), \
         patch("main.RadarPipeline") as mock_pipeline, \
         patch.object(sys, "argv", ["main.py", "--shadow"]):
        mock_pipeline.return_value.run.return_value = {
            "technologies": [{"id": "react", "name": "React", "quadrant": "tools", "ring": "adopt", "description": "UI"}],
            "watchlist": [],
            "meta": {},
        }

        exit_code = main()

    assert exit_code == 0

    payload = json.loads(public_file.read_text())
    shadow_gate = payload["meta"]["shadowGate"]
    assert_skip_shadow_gate_defaults(shadow_gate)


def test_shadow_only_without_baseline_persists_stable_shadow_gate_contract(tmp_path):
    from main import main
    from etl.config import ETLConfig, OutputConfig

    current_file = tmp_path / "data.ai.json"
    current_file.write_text(
        json.dumps(
            {
                "technologies": [{"id": "react", "name": "React"}],
                "watchlist": [],
                "meta": {},
            }
        )
    )

    cfg = ETLConfig(output=OutputConfig(public_file=str(current_file)))

    with patch("main.load_etl_config", return_value=cfg), \
         patch("main.RadarPipeline") as mock_pipeline, \
         patch.object(
             sys,
             "argv",
             [
                 "main.py",
                 "--shadow-only",
                 "--shadow-current",
                 str(current_file),
             ],
         ):
        exit_code = main()

    assert exit_code == 0
    mock_pipeline.assert_not_called()

    payload = json.loads(current_file.read_text())
    shadow_gate = payload["meta"]["shadowGate"]
    assert_skip_shadow_gate_defaults(shadow_gate)


def test_shadow_only_warn_and_fail_keep_baseline_leader_state_in_meta(tmp_path):
    from main import main
    from etl.config import ETLConfig, OutputConfig

    current_file = tmp_path / "data.ai.json"
    baseline_file = tmp_path / "baseline.json"
    report_file = tmp_path / "shadow_eval.json"

    baseline_leader_state = {
        "stableLeaders": ["kubernetes", "react"],
        "candidateChanges": {
            "bun:added": {
                "leaderId": "bun",
                "changeType": "added",
                "consecutiveCount": 2,
                "firstSeenRun": "run-2",
                "lastSeenRun": "run-3",
            }
        },
        "promotedChanges": [],
        "lastRunId": "run-3",
        "promotionRuns": 3,
    }

    baseline_payload = {
        "technologies": [{"id": "react", "marketScore": 98}, {"id": "kubernetes", "marketScore": 97}],
        "watchlist": [],
        "meta": {"shadowGate": {"leaderState": baseline_leader_state}},
    }
    current_payload = {
        "technologies": [{"id": "react", "marketScore": 98}, {"id": "kubernetes", "marketScore": 97}],
        "watchlist": [],
        "meta": {},
    }

    baseline_file.write_text(json.dumps(baseline_payload))
    current_file.write_text(json.dumps(current_payload))

    cfg = ETLConfig(output=OutputConfig(public_file=str(current_file)))

    with patch("main.load_etl_config", return_value=cfg), \
         patch("main.RadarPipeline") as mock_pipeline, \
         patch.object(
             sys,
             "argv",
             [
                 "main.py",
                 "--shadow-only",
                 "--shadow-baseline",
                 str(baseline_file),
                 "--shadow-current",
                 str(current_file),
                 "--shadow-output",
                 str(report_file),
                 "--shadow-threshold-core-overlap",
                 "1.1",
                 "--shadow-threshold-leader-coverage",
                 "0.0",
                 "--shadow-threshold-watchlist-recall",
                 "0.0",
                 "--shadow-threshold-llm-reduction",
                 "0.0",
             ],
         ):
        exit_code = main()

    assert exit_code == 1
    mock_pipeline.assert_not_called()

    payload = json.loads(current_file.read_text())
    leader_state = payload["meta"]["shadowGate"]["leaderState"]
    assert leader_state == baseline_leader_state


def test_shadow_only_warn_persists_updated_candidate_leader_state(tmp_path):
    from main import main
    from etl.config import ETLConfig, OutputConfig

    current_file = tmp_path / "data.ai.json"
    baseline_file = tmp_path / "baseline.json"
    report_file = tmp_path / "shadow_eval.json"

    baseline_payload = {
        "technologies": [{"id": "react", "marketScore": 98}, {"id": "kubernetes", "marketScore": 97}],
        "watchlist": [],
        "meta": {"shadowGate": {"leaderState": {"stableLeaders": ["kubernetes", "react"], "candidateChanges": {}, "promotionRuns": 3}}},
    }
    current_payload = {
        "technologies": [
            {"id": "react", "marketScore": 98},
            {"id": "kubernetes", "marketScore": 97},
            {"id": "bun", "marketScore": 99},
        ],
        "watchlist": [],
        "meta": {},
    }

    baseline_file.write_text(json.dumps(baseline_payload))
    current_file.write_text(json.dumps(current_payload))

    cfg = ETLConfig(output=OutputConfig(public_file=str(current_file)))

    with patch("main.load_etl_config", return_value=cfg), \
         patch("main.RadarPipeline") as mock_pipeline, \
         patch.object(
             sys,
             "argv",
             [
                 "main.py",
                 "--shadow-only",
                 "--shadow-baseline",
                 str(baseline_file),
                 "--shadow-current",
                 str(current_file),
                 "--shadow-output",
                 str(report_file),
                 "--shadow-threshold-core-overlap",
                 "0.0",
                 "--shadow-threshold-leader-coverage",
                 "0.0",
                 "--shadow-threshold-watchlist-recall",
                 "0.0",
                 "--shadow-threshold-llm-reduction",
                 "0.0",
             ],
         ):
        exit_code = main()

    assert exit_code == 0
    mock_pipeline.assert_not_called()

    payload = json.loads(current_file.read_text())
    shadow_gate = payload["meta"]["shadowGate"]
    assert shadow_gate["status"] == "warn"
    assert shadow_gate["leaderTransitionSummary"] == {
        "candidateCount": 1,
        "promotedCount": 0,
    }
    candidate_change = shadow_gate["leaderState"]["candidateChanges"]["bun:added"]
    assert candidate_change["leaderId"] == "bun"
    assert candidate_change["changeType"] == "added"
    assert candidate_change["consecutiveCount"] == 1
    assert candidate_change["firstSeenRun"]
    assert candidate_change["lastSeenRun"]


def test_main_applies_max_technologies_to_distribution_target(tmp_path):
    from main import main
    from etl.config import ETLConfig, OutputConfig

    public_file = tmp_path / "data.ai.json"
    cfg = ETLConfig(output=OutputConfig(public_file=str(public_file)))

    with patch("main.load_etl_config", return_value=cfg), \
         patch("main.RadarPipeline") as mock_pipeline, \
         patch.object(sys, "argv", ["main.py", "--max-technologies", "6"]):
        mock_pipeline.return_value.run.return_value = {
            "technologies": [],
            "watchlist": [],
            "meta": {},
        }

        exit_code = main()

    assert exit_code == 0
    passed_config = mock_pipeline.call_args.kwargs["config"]
    assert passed_config.distribution.target_total == 6
    assert not hasattr(passed_config, "deep_scan")


def test_main_defaults_support_market_faithful_base_radar_targets():
    from etl.config import load_etl_config

    config = load_etl_config("scripts/config.yaml")

    assert config.distribution.target_total == 40
    assert config.distribution.min_per_quadrant == 2
    assert config.distribution.max_per_quadrant == 12
    assert config.distribution.min_per_ring == 8
    assert config.distribution.target_per_ring == 10
    assert config.distribution.max_per_ring == 15


def test_main_rejects_invalid_sources_argument(tmp_path, capsys):
    from main import main
    from etl.config import ETLConfig, OutputConfig

    public_file = tmp_path / "data.ai.json"
    cfg = ETLConfig(output=OutputConfig(public_file=str(public_file)))

    with patch("main.load_etl_config", return_value=cfg), \
         patch("main.RadarPipeline") as mock_pipeline, \
         patch.object(sys, "argv", ["main.py", "--sources", "github"]):
        exit_code = main()

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "Invalid --sources value" in captured.out
    mock_pipeline.assert_not_called()


def test_shadow_only_pass_persists_updated_stable_leader_state(tmp_path):
    from main import main
    from etl.config import ETLConfig, OutputConfig

    current_file = tmp_path / "data.ai.json"
    baseline_file = tmp_path / "baseline.json"
    report_file = tmp_path / "shadow_eval.json"

    baseline_leader_state = {
        "stableLeaders": ["kubernetes", "react"],
        "candidateChanges": {
            "bun:added": {
                "leaderId": "bun",
                "changeType": "added",
                "consecutiveCount": 2,
                "firstSeenRun": "run-2",
                "lastSeenRun": "run-3",
            }
        },
        "promotedChanges": [],
        "lastRunId": "run-3",
        "promotionRuns": 3,
    }

    baseline_payload = {
        "technologies": [{"id": "react", "marketScore": 98}, {"id": "kubernetes", "marketScore": 97}],
        "watchlist": [],
        "meta": {"shadowGate": {"leaderState": baseline_leader_state}},
    }
    current_payload = {
        "technologies": [
            {"id": "react", "marketScore": 98},
            {"id": "kubernetes", "marketScore": 97},
            {"id": "bun", "marketScore": 99},
        ],
        "watchlist": [],
        "meta": {},
    }

    baseline_file.write_text(json.dumps(baseline_payload))
    current_file.write_text(json.dumps(current_payload))

    cfg = ETLConfig(output=OutputConfig(public_file=str(current_file)))

    with patch("main.load_etl_config", return_value=cfg), \
         patch("main.RadarPipeline") as mock_pipeline, \
         patch.object(
             sys,
             "argv",
             [
                 "main.py",
                 "--shadow-only",
                 "--shadow-baseline",
                 str(baseline_file),
                 "--shadow-current",
                 str(current_file),
                 "--shadow-output",
                 str(report_file),
                 "--shadow-threshold-core-overlap",
                 "0.0",
                 "--shadow-threshold-leader-coverage",
                 "0.0",
                 "--shadow-threshold-watchlist-recall",
                 "0.0",
                 "--shadow-threshold-llm-reduction",
                 "0.0",
             ],
         ):
        exit_code = main()

    assert exit_code == 0
    mock_pipeline.assert_not_called()

    payload = json.loads(current_file.read_text())
    leader_state = payload["meta"]["shadowGate"]["leaderState"]
    assert leader_state["stableLeaders"] == ["bun", "kubernetes", "react"]
    assert leader_state["candidateChanges"] == {}
    assert leader_state["promotedChanges"] == [{"leaderId": "bun", "changeType": "added"}]
    assert leader_state["promotionRuns"] == 3


def test_main_preserves_run_metrics_in_public_meta(tmp_path):
    from main import main
    from etl.config import ETLConfig, OutputConfig

    public_file = tmp_path / "data.ai.json"
    cfg = ETLConfig(output=OutputConfig(public_file=str(public_file)))

    with patch("main.load_etl_config", return_value=cfg), \
         patch("main.RadarPipeline") as mock_pipeline, \
         patch.object(sys, "argv", ["main.py"]):
        mock_pipeline.return_value.run.return_value = {
            "technologies": [],
            "watchlist": [],
            "meta": {
                "pipeline": {
                    "runMetrics": {
                        "sources": {
                            "github_trending": {
                                "records": 20,
                                "durationSeconds": 1.2,
                                "failures": 0,
                            }
                        }
                    }
                }
            },
        }

        exit_code = main()

    assert exit_code == 0
    payload = json.loads(public_file.read_text())
    assert payload["meta"]["pipeline"]["runMetrics"]["sources"]["github_trending"]["records"] == 20
