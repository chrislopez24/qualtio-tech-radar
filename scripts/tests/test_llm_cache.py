"""Tests for LLM decision cache with drift invalidation"""


def test_llm_cache_hits_when_signal_drift_is_small(tmp_path):
    from etl.llm_cache import LLMDecisionCache

    cache = LLMDecisionCache(tmp_path / "llm_cache.json")
    key = cache.make_key("react", "hf:model", "v1", {"market_score": 80.0, "hn_heat": 20.0})
    cache.put(key, {"strategic_value": "high"})

    hit = cache.get_if_fresh(
        name="react",
        model="hf:model",
        prompt_version="v1",
        features={"market_score": 81.0, "hn_heat": 21.0},
        max_drift=3.0,
    )
    assert hit is not None


def test_llm_cache_misses_when_drift_exceeds_threshold(tmp_path):
    from etl.llm_cache import LLMDecisionCache

    cache = LLMDecisionCache(tmp_path / "llm_cache.json")
    key = cache.make_key("react", "hf:model", "v1", {"market_score": 80.0, "hn_heat": 20.0})
    cache.put(key, {"strategic_value": "high"})

    hit = cache.get_if_fresh(
        name="react",
        model="hf:model",
        prompt_version="v1",
        features={"market_score": 100.0, "hn_heat": 50.0},  # Large drift
        max_drift=3.0,
    )
    assert hit is None


def test_llm_cache_misses_when_model_changes(tmp_path):
    from etl.llm_cache import LLMDecisionCache

    cache = LLMDecisionCache(tmp_path / "llm_cache.json")
    key = cache.make_key("react", "hf:model-v1", "v1", {"market_score": 80.0})
    cache.put(key, {"strategic_value": "high"})

    hit = cache.get_if_fresh(
        name="react",
        model="hf:model-v2",  # Different model
        prompt_version="v1",
        features={"market_score": 80.0},
        max_drift=3.0,
    )
    assert hit is None


def test_llm_cache_misses_when_prompt_version_changes(tmp_path):
    from etl.llm_cache import LLMDecisionCache

    cache = LLMDecisionCache(tmp_path / "llm_cache.json")
    key = cache.make_key("react", "hf:model", "v1", {"market_score": 80.0})
    cache.put(key, {"strategic_value": "high"})

    hit = cache.get_if_fresh(
        name="react",
        model="hf:model",
        prompt_version="v2",  # Different version
        features={"market_score": 80.0},
        max_drift=3.0,
    )
    assert hit is None


def test_llm_cache_misses_when_name_changes(tmp_path):
    from etl.llm_cache import LLMDecisionCache

    cache = LLMDecisionCache(tmp_path / "llm_cache.json")
    key = cache.make_key("react", "hf:model", "v1", {"market_score": 80.0})
    cache.put(key, {"strategic_value": "high"})

    hit = cache.get_if_fresh(
        name="vue",  # Different name
        model="hf:model",
        prompt_version="v1",
        features={"market_score": 80.0},
        max_drift=3.0,
    )
    assert hit is None


def test_llm_cache_tolerates_corrupt_cache_file(tmp_path):
    from etl.llm_cache import LLMDecisionCache

    cache_file = tmp_path / "llm_cache.json"
    cache_file.write_text("not valid json {{[")

    cache = LLMDecisionCache(cache_file)
    
    # Should still work despite corrupt file
    hit = cache.get_if_fresh(
        name="react",
        model="hf:model",
        prompt_version="v1",
        features={"market_score": 80.0},
        max_drift=3.0,
    )
    assert hit is None


def test_llm_cache_returns_exact_match_with_zero_drift(tmp_path):
    from etl.llm_cache import LLMDecisionCache

    cache = LLMDecisionCache(tmp_path / "llm_cache.json")
    key = cache.make_key("react", "hf:model", "v1", {"market_score": 80.0, "hn_heat": 20.0})
    cache.put(key, {"strategic_value": "high"})

    hit = cache.get_if_fresh(
        name="react",
        model="hf:model",
        prompt_version="v1",
        features={"market_score": 80.0, "hn_heat": 20.0},
        max_drift=0.0,  # Must be exact match
    )
    assert hit == {"strategic_value": "high"}


def test_llm_cache_key_is_deterministic(tmp_path):
    from etl.llm_cache import LLMDecisionCache

    cache = LLMDecisionCache(tmp_path / "llm_cache.json")
    
    key1 = cache.make_key("react", "hf:model", "v1", {"market_score": 80.0, "hn_heat": 20.0})
    key2 = cache.make_key("react", "hf:model", "v1", {"hn_heat": 20.0, "market_score": 80.0})
    
    # Order of features should not matter
    assert key1 == key2


def test_llm_cache_persists_between_instances(tmp_path):
    from etl.llm_cache import LLMDecisionCache

    # First instance
    cache1 = LLMDecisionCache(tmp_path / "llm_cache.json")
    key = cache1.make_key("react", "hf:model", "v1", {"market_score": 80.0})
    cache1.put(key, {"strategic_value": "high"})

    # Second instance - should load from disk
    cache2 = LLMDecisionCache(tmp_path / "llm_cache.json")
    hit = cache2.get_if_fresh(
        name="react",
        model="hf:model",
        prompt_version="v1",
        features={"market_score": 80.0},
        max_drift=0.0,
    )
    assert hit == {"strategic_value": "high"}


def test_llm_cache_errors_do_not_block_pipeline(tmp_path):
    """Test that cache errors (e.g., permission denied) don't crash the pipeline.
    
    The cache should be a transparent optimization - if it fails, the pipeline
    should continue without it. Cache stores values in-memory even if disk
    persistence fails.
    """
    from etl.llm_cache import LLMDecisionCache
    import os

    cache_file = tmp_path / "llm_cache.json"
    
    # Create a cache and store a value
    cache = LLMDecisionCache(cache_file)
    key = cache.make_key("react", "hf:model", "v1", {"market_score": 80.0})
    cache.put(key, {"strategic_value": "high"})
    
    # Now make the file read-only to simulate permission errors
    os.chmod(cache_file, 0o444)
    
    try:
        # Create a new cache instance pointing to the read-only file
        read_only_cache = LLMDecisionCache(cache_file)
        
        # Attempt to read should work (file exists and is readable)
        hit = read_only_cache.get_if_fresh(
            name="react",
            model="hf:model",
            prompt_version="v1",
            features={"market_score": 80.0},
            max_drift=0.0,
        )
        assert hit == {"strategic_value": "high"}
        
        # Attempt to write should fail gracefully (not raise exception)
        # The cache stores in memory even if disk write fails
        new_key = read_only_cache.make_key("vue", "hf:model", "v1", {"market_score": 70.0})
        read_only_cache.put(new_key, {"strategic_value": "medium"})
        
        # The cache should still be usable for reads (in-memory)
        hit2 = read_only_cache.get_if_fresh(
            name="vue",
            model="hf:model",
            prompt_version="v1",
            features={"market_score": 70.0},
            max_drift=0.0,
        )
        # Cache should return the in-memory value even though disk write failed
        assert hit2 == {"strategic_value": "medium"}
        
    finally:
        # Restore permissions for cleanup
        os.chmod(cache_file, 0o644)
