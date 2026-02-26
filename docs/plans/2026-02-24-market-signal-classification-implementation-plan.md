# Market Signal Classification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement a market-driven radar classification pipeline so rings reflect external momentum (GitHub + Hacker News + Google Trends) instead of collapsing to all `adopt`.

**Architecture:** Add deterministic market-scoring and ring-assignment layers on top of existing ETL phases. Sources provide normalized external signals, a history store enables temporal trend calculation, and a ring engine applies threshold + hysteresis + distribution guardrails. Quadrants remain deterministic-first with AI fallback.

**Tech Stack:** Python 3.12, pytest, requests, pytrends, existing ETL package (`scripts/etl/*`), GitHub Actions weekly workflow.

---

### Task 1: Extend ETL configuration for market scoring and history

**Files:**
- Modify: `scripts/config.yaml`
- Modify: `scripts/etl/config.py`
- Test: `scripts/tests/test_config_schema.py`

**Step 1: Write the failing test**

```python
def test_config_includes_market_scoring_and_history_sections():
    from etl.config import load_etl_config

    cfg = load_etl_config("scripts/config.yaml")
    assert cfg.scoring.weights.github_momentum > 0
    assert cfg.history.enabled is True
    assert cfg.history.file.endswith("data.ai.history.json")
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest scripts/tests/test_config_schema.py::test_config_includes_market_scoring_and_history_sections -q`
Expected: FAIL (missing config sections/fields)

**Step 3: Implement minimal config schema + defaults**

Add typed config blocks in `scripts/etl/config.py`:

- `ScoringConfig` (`weights`, `thresholds`, `hysteresis`)
- `HistoryConfig` (`enabled`, `file`, `max_weeks`)
- `DistributionGuardrailConfig` (`max_ring_ratio`, `enabled`)

Update `scripts/config.yaml` with default weights and initial Google seed topics.

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest scripts/tests/test_config_schema.py::test_config_includes_market_scoring_and_history_sections -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/config.yaml scripts/etl/config.py scripts/tests/test_config_schema.py
git commit -m "feat(etl): add market scoring and history config sections"
```

---

### Task 2: Replace GitHub popularity query with momentum-oriented collection

**Files:**
- Modify: `scripts/etl/sources/github_scraper.py`
- Modify: `scripts/etl/sources/github_trending.py`
- Test: `scripts/tests/test_github_trending_source.py`

**Step 1: Write the failing test**

```python
def test_github_source_combines_recent_created_and_recent_pushed_queries():
    from etl.config import GitHubTrendingSource as GitHubTrendingConfig
    from etl.sources.github_trending import GitHubTrendingSource

    config = GitHubTrendingConfig(enabled=True, language="all", time_range="weekly")
    source = GitHubTrendingSource(config=config)

    source._fetch_trending_repos(language=None, time_range="weekly")
    # assert internal scraper called with created/pushed windows, not stars-only query
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest scripts/tests/test_github_trending_source.py::test_github_source_combines_recent_created_and_recent_pushed_queries -q`
Expected: FAIL (stars-only path still used)

**Step 3: Implement minimal momentum query strategy**

Implement in scraper/source:

- query A: `created:>=<window>` + sorting strategy
- query B: `pushed:>=<window>` + sorting strategy
- merge/dedupe by repo `full_name`
- compute source-side momentum proxy in raw data

Keep existing language filter and rate limiting behavior.

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest scripts/tests/test_github_trending_source.py::test_github_source_combines_recent_created_and_recent_pushed_queries -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/etl/sources/github_scraper.py scripts/etl/sources/github_trending.py scripts/tests/test_github_trending_source.py
git commit -m "feat(etl): switch github ingestion to momentum-oriented queries"
```

---

### Task 3: Improve Hacker News technology extraction quality

**Files:**
- Modify: `scripts/etl/sources/hackernews.py`
- Modify: `scripts/etl/pipeline.py`
- Test: `scripts/tests/test_hackernews_source.py`
- Test: `scripts/tests/test_pipeline_flow.py`

**Step 1: Write the failing test**

```python
def test_extract_tech_name_prefers_known_tech_tokens_over_first_word():
    from etl.pipeline import RadarPipeline

    pipeline = RadarPipeline()
    name = pipeline._extract_tech_name("Show HN: Building with PostgreSQL and Rust")
    assert name in {"postgresql", "rust"}
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest scripts/tests/test_pipeline_flow.py::TestPipelineFlow::test_extract_tech_name_prefers_known_tech_tokens_over_first_word -q`
Expected: FAIL (current behavior returns first non-stopword)

**Step 3: Implement minimal deterministic extractor**

Add extraction logic that:

- uses curated keyword/alias list
- normalizes punctuation/case
- prefers known tech entities over generic terms
- returns `None` when no tech-like token is found

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest scripts/tests/test_pipeline_flow.py::TestPipelineFlow::test_extract_tech_name_prefers_known_tech_tokens_over_first_word -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/etl/sources/hackernews.py scripts/etl/pipeline.py scripts/tests/test_hackernews_source.py scripts/tests/test_pipeline_flow.py
git commit -m "feat(etl): improve HN technology extraction for signal quality"
```

---

### Task 4: Wire Google Trends into collection phase with seed topics

**Files:**
- Modify: `scripts/etl/pipeline.py`
- Modify: `scripts/etl/config.py`
- Modify: `scripts/config.yaml`
- Test: `scripts/tests/test_pipeline_flow.py`
- Test: `scripts/tests/test_google_trends_source.py`

**Step 1: Write the failing test**

```python
def test_pipeline_collects_google_trends_when_enabled():
    from etl.pipeline import RadarPipeline
    from etl.config import ETLConfig

    config = ETLConfig()
    config.sources.google_trends.enabled = True
    config.sources.google_trends.seed_topics = ["ai", "devops"]

    pipeline = RadarPipeline(config=config)
    technologies = pipeline._collect_sources()
    assert isinstance(technologies, list)
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest scripts/tests/test_pipeline_flow.py::TestPipelineFlow::test_pipeline_collects_google_trends_when_enabled -q`
Expected: FAIL (source not wired in pipeline)

**Step 3: Implement minimal pipeline integration**

- Instantiate `GoogleTrendsSource` in `_init_components`.
- Include Google signals in `_collect_sources` when enabled.
- Ensure dedupe merges cross-source records without dropping signal metadata.

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest scripts/tests/test_pipeline_flow.py::TestPipelineFlow::test_pipeline_collects_google_trends_when_enabled -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/etl/pipeline.py scripts/etl/config.py scripts/config.yaml scripts/tests/test_pipeline_flow.py scripts/tests/test_google_trends_source.py
git commit -m "feat(etl): integrate google trends signals into source collection"
```

---

### Task 5: Add deterministic market scoring module

**Files:**
- Create: `scripts/etl/market_scoring.py`
- Test: `scripts/tests/test_market_scoring.py`
- Modify: `scripts/etl/pipeline.py`

**Step 1: Write the failing test**

```python
def test_market_score_uses_weighted_external_signals():
    from etl.market_scoring import score_technology

    item = {
        "gh_momentum": 80,
        "gh_popularity": 60,
        "hn_heat": 50,
        "google_momentum": 40,
    }
    score = score_technology(item)
    assert round(score, 2) == 59.0
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest scripts/tests/test_market_scoring.py::test_market_score_uses_weighted_external_signals -q`
Expected: FAIL (module/function does not exist)

**Step 3: Implement minimal scoring API**

Implement:

- `score_technology(signals, weights=None) -> float`
- clamp output to `[0, 100]`
- `calculate_confidence(source_count, variance)` helper

Integrate in pipeline right after normalization and before ring assignment.

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest scripts/tests/test_market_scoring.py::test_market_score_uses_weighted_external_signals -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/etl/market_scoring.py scripts/tests/test_market_scoring.py scripts/etl/pipeline.py
git commit -m "feat(etl): add deterministic external market scoring module"
```

---

### Task 6: Add history store for temporal trend and moved calculation

**Files:**
- Create: `scripts/etl/history_store.py`
- Modify: `scripts/etl/pipeline.py`
- Test: `scripts/tests/test_history_store.py`

**Step 1: Write the failing test**

```python
def test_history_store_retains_rolling_weeks_and_returns_previous_snapshot(tmp_path):
    from etl.history_store import HistoryStore

    store = HistoryStore(tmp_path / "history.json", max_weeks=2)
    store.append_snapshot({"technologies": [{"id": "react", "ring": "trial"}]})
    store.append_snapshot({"technologies": [{"id": "react", "ring": "adopt"}]})

    prev = store.get_previous_snapshot()
    assert prev is not None
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest scripts/tests/test_history_store.py::test_history_store_retains_rolling_weeks_and_returns_previous_snapshot -q`
Expected: FAIL (store not implemented)

**Step 3: Implement minimal history store**

Implement JSON-backed store with:

- append snapshot
- keep rolling `max_weeks`
- fetch previous snapshot
- safe behavior on missing/corrupt file

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest scripts/tests/test_history_store.py::test_history_store_retains_rolling_weeks_and_returns_previous_snapshot -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/etl/history_store.py scripts/etl/pipeline.py scripts/tests/test_history_store.py
git commit -m "feat(etl): add rolling history store for temporal trend analysis"
```

---

### Task 7: Implement ring engine with hysteresis and anti-collapse guardrails

**Files:**
- Create: `scripts/etl/ring_assignment.py`
- Modify: `scripts/etl/pipeline.py`
- Test: `scripts/tests/test_ring_assignment.py`

**Step 1: Write the failing test**

```python
def test_ring_assignment_avoids_all_adopt_distribution():
    from etl.ring_assignment import assign_rings

    items = [{"id": str(i), "market_score": 70 + (i % 3)} for i in range(24)]
    assigned = assign_rings(items, previous=None)
    rings = {item["ring"] for item in assigned}
    assert len(rings) > 1
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest scripts/tests/test_ring_assignment.py::test_ring_assignment_avoids_all_adopt_distribution -q`
Expected: FAIL (engine missing)

**Step 3: Implement minimal ring assignment logic**

Implement in two stages:

1. absolute threshold assignment from `market_score` + `trend_delta`
2. guardrails:
   - hysteresis against previous ring
   - cool-down for oscillation
   - percentile fallback rebalance if one ring exceeds configured ratio

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest scripts/tests/test_ring_assignment.py::test_ring_assignment_avoids_all_adopt_distribution -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/etl/ring_assignment.py scripts/etl/pipeline.py scripts/tests/test_ring_assignment.py
git commit -m "feat(etl): add ring assignment engine with hysteresis and guardrails"
```

---

### Task 8: Integrate trend and moved fields into public output contract

**Files:**
- Modify: `scripts/etl/pipeline.py`
- Modify: `scripts/etl/output_generator.py`
- Test: `scripts/tests/test_output_generator.py`
- Test: `scripts/tests/test_pipeline_flow.py`

**Step 1: Write the failing test**

```python
def test_output_contains_market_score_trend_and_moved():
    from etl.pipeline import RadarPipeline

    pipeline = RadarPipeline()
    output = pipeline._generate_output([])
    assert "technologies" in output
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest scripts/tests/test_output_generator.py::test_output_contains_market_score_trend_and_moved -q`
Expected: FAIL (fields missing)

**Step 3: Implement minimal output changes**

Ensure each technology includes:

- `marketScore`
- `trend`
- `moved`
- compact `signals` summary

Maintain sanitization behavior and valid JSON format.

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest scripts/tests/test_output_generator.py::test_output_contains_market_score_trend_and_moved -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/etl/pipeline.py scripts/etl/output_generator.py scripts/tests/test_output_generator.py scripts/tests/test_pipeline_flow.py
git commit -m "feat(etl): publish market score and movement metadata in radar output"
```

---

### Task 9: Update weekly workflow and docs for market-based classification

**Files:**
- Modify: `.github/workflows/weekly-update.yml`
- Modify: `README.md`
- Modify: `docs/etl-architecture.md`
- Modify: `docs/etl-ops-runbook.md`
- Test: `scripts/tests/test_workflow_contract.py`

**Step 1: Write the failing test**

```python
def test_workflow_persists_history_file_and_public_ai_data():
    from pathlib import Path
    text = Path(".github/workflows/weekly-update.yml").read_text()
    assert "src/data/data.ai.history.json" in text
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest scripts/tests/test_workflow_contract.py::test_workflow_persists_history_file_and_public_ai_data -q`
Expected: FAIL (history artifact not handled yet)

**Step 3: Implement workflow + docs updates**

- Commit both `src/data/data.ai.json` and `src/data/data.ai.history.json` when changed.
- Document new scoring/ring semantics and troubleshooting guidance.
- Add note on determinism and anti-collapse behavior.

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest scripts/tests/test_workflow_contract.py::test_workflow_persists_history_file_and_public_ai_data -q`
Expected: PASS

**Step 5: Commit**

```bash
git add .github/workflows/weekly-update.yml README.md docs/etl-architecture.md docs/etl-ops-runbook.md scripts/tests/test_workflow_contract.py
git commit -m "docs(ci): align workflow and docs with market-signal ring classification"
```

---

## Final Verification Checklist

Run in this order:

1. `source .venv/bin/activate && pytest scripts/tests/test_market_scoring.py scripts/tests/test_ring_assignment.py scripts/tests/test_history_store.py -q`
2. `source .venv/bin/activate && pytest scripts/tests/test_pipeline_flow.py scripts/tests/test_output_generator.py scripts/tests/test_workflow_contract.py -q`
3. `source .venv/bin/activate && python scripts/main.py --dry-run`
4. `npm run build`
5. `node -e "const d=require('./src/data/data.ai.json');const c=d.technologies.reduce((a,t)=>(a[t.ring]=(a[t.ring]||0)+1,a),{});console.log(c)"`

Expected outcomes:

- tests pass
- dry-run succeeds
- frontend build succeeds
- ring distribution is non-degenerate (more than one ring present)

## Success Criteria

- Ring assignment reflects external market momentum, not only historical popularity.
- Weekly outputs include trend and movement based on persisted history.
- No collapse to all-`adopt` in normal runs.
- Classification remains deterministic for same input snapshot.
