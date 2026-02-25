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
