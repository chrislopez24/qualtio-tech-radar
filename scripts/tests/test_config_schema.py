import pytest
from pathlib import Path


def test_config_loads_with_defaults(tmp_path):
    from etl.config import load_etl_config
    cfg = load_etl_config("scripts/config.yaml")
    assert cfg.sources.github_trending.enabled is True


def test_default_model_uses_hf_prefix_for_synthetic_api():
    from etl.config import load_etl_config

    cfg = load_etl_config("does-not-exist.yaml")

    assert cfg.classification.model.startswith("hf:")


def test_config_includes_market_scoring_and_history_sections():
    from etl.config import load_etl_config

    cfg = load_etl_config("scripts/config.yaml")
    assert cfg.scoring.weights.github_momentum > 0
    assert cfg.history.enabled is True
    assert cfg.history.file.endswith("data.ai.history.json")
