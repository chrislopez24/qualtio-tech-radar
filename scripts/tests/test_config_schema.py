import pytest
from pathlib import Path


def test_config_loads_with_defaults(tmp_path):
    from etl.config import load_etl_config
    cfg = load_etl_config("scripts/config.yaml")
    assert cfg.sources.github_trending.enabled is True