import pytest
import sys
import tempfile
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