# LLM Call Reduction Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reduce ETL LLM calls by at least 70% while preserving radar output quality and explicitly retaining a growth watchlist.

**Architecture:** Move deterministic quality/scoring/ring logic ahead of semantic AI, then call LLM only for borderline or watchlist candidates that need semantic judgment. Consolidate semantic work into a single call per selected item and add cross-run cache reuse with drift-aware invalidation. Validate with baseline-vs-optimized shadow metrics before default rollout.

**Tech Stack:** Python 3.12, pytest, Pydantic config models, existing ETL modules in `scripts/etl/*`, JSON artifacts in `src/data/*`.

---

### Task 1: Add optimization config contract

**Files:**
- Modify: `scripts/etl/config.py`
- Modify: `scripts/config.yaml`
- Test: `scripts/tests/test_config_schema.py`

**Step 1: Write the failing test**

```python
def test_config_exposes_llm_optimization_controls():
    from etl.config import load_etl_config

    cfg = load_etl_config("scripts/config.yaml")
    assert cfg.llm_optimization.enabled is True
    assert cfg.llm_optimization.max_calls_per_run > 0
    assert 0.0 <= cfg.llm_optimization.borderline_band <= 20.0
    assert cfg.llm_optimization.watchlist_ratio > 0.0
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest scripts/tests/test_config_schema.py::test_config_exposes_llm_optimization_controls -q`
Expected: FAIL with missing `llm_optimization` fields.

**Step 3: Write minimal implementation**

```python
class LLMOptimizationConfig(BaseModel):
    enabled: bool = True
    max_calls_per_run: int = Field(ge=1, default=40)
    borderline_band: float = Field(ge=0.0, le=20.0, default=5.0)
    watchlist_ratio: float = Field(gt=0.0, lt=1.0, default=0.25)
    cache_enabled: bool = True
```

Wire it into `ETLConfig` and `scripts/config.yaml` with defaults.

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest scripts/tests/test_config_schema.py::test_config_exposes_llm_optimization_controls -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/etl/config.py scripts/config.yaml scripts/tests/test_config_schema.py
git commit -m "feat(etl): add llm optimization config controls"
```

---

### Task 2: Implement deterministic candidate selector (Core + Watchlist + Borderline)

**Files:**
- Create: `scripts/etl/candidate_selector.py`
- Modify: `scripts/etl/pipeline.py`
- Test: `scripts/tests/test_candidate_selector.py`

**Step 1: Write the failing test**

```python
def test_selector_splits_core_watchlist_and_borderline():
    from etl.candidate_selector import select_candidates

    items = [
        {"id": "react", "market_score": 92, "trend_delta": 3, "confidence": 0.9},
        {"id": "new-framework", "market_score": 58, "trend_delta": 18, "confidence": 0.6},
        {"id": "edge-tool", "market_score": 61, "trend_delta": 1, "confidence": 0.45},
    ]
    out = select_candidates(items, target_total=10, watchlist_ratio=0.3, borderline_band=5.0)
    assert "react" in out.core_ids
    assert "new-framework" in out.watchlist_ids
    assert "edge-tool" in out.borderline_ids
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest scripts/tests/test_candidate_selector.py::test_selector_splits_core_watchlist_and_borderline -q`
Expected: FAIL because selector does not exist.

**Step 3: Write minimal implementation**

```python
@dataclass
class CandidateSelection:
    core_ids: list[str]
    watchlist_ids: list[str]
    borderline_ids: list[str]


def select_candidates(items, target_total, watchlist_ratio, borderline_band):
    ...
```

Rules:
- Core by market score + confidence.
- Watchlist by trend delta (growth).
- Borderline based on distance to ring thresholds and low deterministic confidence.

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest scripts/tests/test_candidate_selector.py::test_selector_splits_core_watchlist_and_borderline -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/etl/candidate_selector.py scripts/etl/pipeline.py scripts/tests/test_candidate_selector.py
git commit -m "feat(etl): add deterministic core-watchlist candidate selector"
```

---

### Task 3: Add LLM decision cache with drift invalidation

**Files:**
- Create: `scripts/etl/llm_cache.py`
- Modify: `scripts/etl/pipeline.py`
- Test: `scripts/tests/test_llm_cache.py`

**Step 1: Write the failing test**

```python
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
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest scripts/tests/test_llm_cache.py::test_llm_cache_hits_when_signal_drift_is_small -q`
Expected: FAIL because cache module does not exist.

**Step 3: Write minimal implementation**

```python
class LLMDecisionCache:
    def make_key(self, name, model, prompt_version, features):
        ...

    def get_if_fresh(self, name, model, prompt_version, features, max_drift):
        ...

    def put(self, key, value):
        ...
```

Store JSON safely, tolerate corrupt cache, and never block pipeline on cache errors.

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest scripts/tests/test_llm_cache.py::test_llm_cache_hits_when_signal_drift_is_small -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/etl/llm_cache.py scripts/etl/pipeline.py scripts/tests/test_llm_cache.py
git commit -m "feat(etl): add drift-aware llm decision cache"
```

---

### Task 4: Consolidate semantic LLM decision into one pass

**Files:**
- Modify: `scripts/etl/classifier.py`
- Modify: `scripts/etl/ai_filter.py`
- Test: `scripts/tests/test_classifier.py`
- Test: `scripts/tests/test_ai_filter.py`

**Step 1: Write the failing test**

```python
def test_classifier_returns_semantic_decision_with_strategic_value():
    from etl.classifier import TechnologyClassifier

    classifier = TechnologyClassifier(api_key="test-key")
    result = classifier._parse_response(
        '{"name":"React","quadrant":"tools","ring":"adopt","description":"UI","confidence":0.9,"trend":"up","strategic_value":"high","rationale":"..."}',
        "React",
    )
    assert hasattr(result, "rationale")
    assert hasattr(result, "confidence")
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest scripts/tests/test_classifier.py::test_classifier_returns_semantic_decision_with_strategic_value -q`
Expected: FAIL due missing strategic decision contract.

**Step 3: Write minimal implementation**

```python
class ClassificationSchema(BaseModel):
    ...
    strategic_value: str = "medium"
```

Then either:
- retire per-item `_ai_evaluate` in `ai_filter` for optimized mode, or
- gate it so optimized path uses classifier semantic payload only.

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest scripts/tests/test_classifier.py::test_classifier_returns_semantic_decision_with_strategic_value -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/etl/classifier.py scripts/etl/ai_filter.py scripts/tests/test_classifier.py scripts/tests/test_ai_filter.py
git commit -m "refactor(etl): consolidate semantic llm decision to single pass"
```

---

### Task 5: Reorder pipeline to selective LLM and budget enforcement

**Files:**
- Modify: `scripts/etl/pipeline.py`
- Test: `scripts/tests/test_pipeline_flow.py`

**Step 1: Write the failing test**

```python
def test_pipeline_calls_llm_only_for_borderline_candidates(mocker):
    from etl.pipeline import RadarPipeline

    pipeline = RadarPipeline()
    mock_classify = mocker.patch.object(pipeline.classifier, "classify_batch", return_value=[])

    pipeline.run()
    assert mock_classify.call_count <= 1
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest scripts/tests/test_pipeline_flow.py::TestPipelineFlow::test_pipeline_calls_llm_only_for_borderline_candidates -q`
Expected: FAIL due current per-item semantic flow.

**Step 3: Write minimal implementation**

```python
# pipeline flow sketch
technologies = self._collect_sources()
technologies = self._normalize_and_dedupe(technologies)
technologies = self._apply_market_scoring(technologies)
selection = self._select_candidates(technologies)
semantic_items = self._run_selective_llm(selection)
```

Enforce `max_calls_per_run`, prioritize by uncertainty, and keep deterministic fallback when budget is exhausted.

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest scripts/tests/test_pipeline_flow.py::TestPipelineFlow::test_pipeline_calls_llm_only_for_borderline_candidates -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/etl/pipeline.py scripts/tests/test_pipeline_flow.py
git commit -m "feat(etl): apply selective llm policy with per-run budget"
```

---

### Task 6: Add baseline-vs-optimized shadow quality evaluator

**Files:**
- Create: `scripts/etl/shadow_eval.py`
- Modify: `scripts/main.py`
- Test: `scripts/tests/test_shadow_eval.py`

**Step 1: Write the failing test**

```python
def test_shadow_eval_computes_quality_contract():
    from etl.shadow_eval import compare_outputs

    baseline = {"technologies": [{"id": "react"}, {"id": "kubernetes"}]}
    optimized = {"technologies": [{"id": "react"}, {"id": "kubernetes"}]}

    report = compare_outputs(baseline, optimized)
    assert report["core_overlap"] == 1.0
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest scripts/tests/test_shadow_eval.py::test_shadow_eval_computes_quality_contract -q`
Expected: FAIL because evaluator does not exist.

**Step 3: Write minimal implementation**

```python
def compare_outputs(baseline, optimized):
    return {
        "core_overlap": ...,
        "leader_coverage": ...,
        "watchlist_recall": ...,
        "llm_call_reduction": ...,
    }
```

Add optional CLI flag for shadow mode and write report artifact to `artifacts/shadow_eval.json`.

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest scripts/tests/test_shadow_eval.py::test_shadow_eval_computes_quality_contract -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/etl/shadow_eval.py scripts/main.py scripts/tests/test_shadow_eval.py
git commit -m "feat(etl): add shadow quality evaluator for llm optimization rollout"
```

---

### Task 7: Update documentation and operational controls

**Files:**
- Modify: `docs/etl-architecture.md`
- Modify: `docs/etl-ops-runbook.md`
- Modify: `README.md`

**Step 1: Write the failing test**

```python
def test_docs_reference_llm_optimization_controls():
    from pathlib import Path

    text = Path("docs/etl-ops-runbook.md").read_text()
    assert "llm_optimization" in text
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest scripts/tests/test_workflow_contract.py::test_docs_reference_llm_optimization_controls -q`
Expected: FAIL (documentation not updated).

**Step 3: Write minimal implementation**

Document:
- selective LLM policy
- cache behavior and invalidation
- quality contract thresholds
- shadow-mode run command and go/no-go criteria

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest scripts/tests/test_workflow_contract.py::test_docs_reference_llm_optimization_controls -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add docs/etl-architecture.md docs/etl-ops-runbook.md README.md
git commit -m "docs(etl): document selective llm policy and quality guardrails"
```

---

### Task 8: Verification gate before rollout

**Files:**
- Modify: `.github/workflows/quarterly-update.yml`
- Test: `scripts/tests/test_workflow_contract.py`

**Step 1: Write the failing test**

```python
def test_quarterly_workflow_supports_shadow_eval_gate():
    from pathlib import Path

    yml = Path(".github/workflows/quarterly-update.yml").read_text()
    assert "shadow" in yml.lower()
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest scripts/tests/test_workflow_contract.py::test_quarterly_workflow_supports_shadow_eval_gate -q`
Expected: FAIL (no rollout gate).

**Step 3: Write minimal implementation**

Add workflow step that:
- runs optimized mode in shadow
- checks thresholds (`core_overlap`, `leader_coverage`, `watchlist_recall`, `llm_call_reduction`)
- blocks publish on quality regression

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest scripts/tests/test_workflow_contract.py::test_quarterly_workflow_supports_shadow_eval_gate -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add .github/workflows/quarterly-update.yml scripts/tests/test_workflow_contract.py
git commit -m "ci: add shadow quality gate before optimized radar publish"
```

---

### Execution Notes

- Use `@test-driven-development` for each task loop (fail -> pass -> refactor).
- Use `@verification-before-completion` before claiming rollout-ready.
- Keep changes DRY and YAGNI: avoid introducing new modules unless they reduce complexity or isolate policy.
