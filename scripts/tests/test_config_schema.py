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


def test_config_exposes_llm_optimization_controls():
    from etl.config import load_etl_config

    cfg = load_etl_config("scripts/config.yaml")
    assert cfg.llm_optimization.enabled is True
    assert cfg.llm_optimization.max_calls_per_run > 0
    assert 0.0 <= cfg.llm_optimization.borderline_band <= 20.0
    assert cfg.llm_optimization.watchlist_ratio > 0.0


def test_config_targets_large_radar_output():
    from etl.config import load_etl_config

    cfg = load_etl_config("scripts/config.yaml")
    assert cfg.distribution.target_total == 75
    assert cfg.distribution.max_per_quadrant >= 18


def test_config_only_exposes_supported_signal_sources():
    from etl.config import load_etl_config

    cfg = load_etl_config("scripts/config.yaml")
    assert set(type(cfg.sources).model_fields.keys()) == {"github_trending", "hackernews", "deps_dev", "osv"}
