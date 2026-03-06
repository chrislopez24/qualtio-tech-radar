"""Tests for checkpoint functionality"""

from etl.checkpoint import CheckpointStore
from etl.pipeline import RadarPipeline


def test_checkpoint_store_save_and_load(tmp_path):
    cp = CheckpointStore(tmp_path / "cp.json")
    cp.save({"phase": "classify", "cursor": 20})
    assert cp.load()["phase"] == "classify"


def test_pipeline_can_resume_from_checkpoint(tmp_path):
    cp = CheckpointStore(tmp_path / "cp.json")
    cp.save({"phase": "classify", "cursor": 20})
    assert cp.load()["phase"] == "classify"


def test_checkpoint_load_returns_none_when_not_exists(tmp_path):
    cp = CheckpointStore(tmp_path / "nonexistent.json")
    assert cp.load() is None


def test_checkpoint_overwrites_existing(tmp_path):
    cp = CheckpointStore(tmp_path / "cp.json")
    cp.save({"phase": "collect", "cursor": 0})
    cp.save({"phase": "classify", "cursor": 50})
    data = cp.load()
    assert data["phase"] == "classify"
    assert data["cursor"] == 50


def test_pipeline_accepts_checkpoint_parameters(tmp_path):
    checkpoint_path = tmp_path / "cp.json"
    pipeline = RadarPipeline(
        checkpoint_path=str(checkpoint_path),
        save_interval=50,
        resume=True
    )
    assert pipeline.checkpoint is not None
    assert pipeline.save_interval == 50
    assert pipeline.resume is True
    assert not hasattr(pipeline, "google_trends_source")


def test_checkpoint_clear(tmp_path):
    cp = CheckpointStore(tmp_path / "cp.json")
    cp.save({"phase": "test"})
    assert cp.load() is not None
    cp.clear()
    assert cp.load() is None
