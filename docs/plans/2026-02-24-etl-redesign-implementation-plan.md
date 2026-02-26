# ETL Redesign (Bazaar-Inspired) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rediseñar por completo el ETL para generar un radar AI robusto (clasificador, filtros, análisis temporal, rate limiting, deep scan), manteniendo como fuentes principales GitHub Trending, Hacker News y Google Trends.

**Architecture:** Se implementará un nuevo paquete `scripts/etl` con pipeline modular por fases: `sources -> normalization -> enrichment -> classification -> filtering -> output`. El ETL producirá dos artefactos (`data.ai.json` público y `data.ai.full.json` interno) y tendrá checkpoint/resume para ejecuciones largas. Se mantendrá `scripts/main.py` como entrypoint compatible para no romper CI ni frontend.

**Tech Stack:** Python 3.12, PyGithub, requests/httpx, OpenAI-compatible (Synthetic), PyYAML, pytest, pytrends, pydantic, backoff/tenacity.

---

## Phase 0: Base técnica y contrato del ETL

### Task 1: Crear estructura del nuevo ETL modular

**Files:**
- Create: `scripts/etl/__init__.py`
- Create: `scripts/etl/models.py`
- Create: `scripts/etl/config.py`
- Create: `scripts/etl/pipeline.py`
- Create: `scripts/etl/errors.py`
- Create: `scripts/tests/test_etl_imports.py`

**Step 1: Write the failing test**

```python
def test_etl_package_imports():
    from etl.pipeline import RadarPipeline
    assert RadarPipeline is not None
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest scripts/tests/test_etl_imports.py -q`
Expected: FAIL (module not found)

**Step 3: Create minimal ETL package skeleton**

Implement class stubs and dataclasses for:
- `SourceTechnology`
- `TechnologySignal`
- `TechnologyClassification`
- `RadarPipeline`

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest scripts/tests/test_etl_imports.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/etl scripts/tests/test_etl_imports.py
git commit -m "feat(etl): scaffold modular ETL package"
```

---

### Task 2: Config schema fuerte con defaults y validación

**Files:**
- Modify: `scripts/config.yaml`
- Modify: `scripts/requirements.txt`
- Create: `scripts/tests/test_config_schema.py`
- Modify: `scripts/etl/config.py`

**Step 1: Write the failing test**

```python
def test_config_loads_with_defaults(tmp_path):
    from etl.config import load_etl_config
    cfg = load_etl_config("scripts/config.yaml")
    assert cfg.sources.github_trending.enabled is True
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest scripts/tests/test_config_schema.py -q`
Expected: FAIL

**Step 3: Implement typed config with Pydantic**

Add sections:
- `sources.github_trending`
- `sources.hackernews`
- `sources.google_trends`
- `classification`
- `filtering`
- `output`
- `rate_limit`
- `checkpoint`
- `deep_scan`

Add dependency: `pydantic>=2.0.0`.

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest scripts/tests/test_config_schema.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/config.yaml scripts/requirements.txt scripts/etl/config.py scripts/tests/test_config_schema.py
git commit -m "feat(etl): add typed config schema with source-specific settings"
```

---

## Phase 1: Ingesta de fuentes (GitHub Trending, HN, Google Trends)

### Task 3: Reescribir fuente GitHub Trending con rate limiter reutilizable

**Files:**
- Create: `scripts/etl/rate_limiter.py`
- Create: `scripts/etl/sources/github_trending.py`
- Create: `scripts/tests/test_github_trending_source.py`
- Modify: `scripts/etl/models.py`

**Step 1: Write the failing test**

```python
def test_github_source_returns_normalized_signals():
    source = GitHubTrendingSource(config=...)
    items = source.fetch()
    assert isinstance(items, list)
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest scripts/tests/test_github_trending_source.py -q`
Expected: FAIL

**Step 3: Implement source + limiter**

Implement:
- cached GitHub core limit check (TTL)
- per-minute throttle
- exponential backoff on 403 / `RateLimitExceededException`
- normalized output model for pipeline

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest scripts/tests/test_github_trending_source.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/etl/rate_limiter.py scripts/etl/sources/github_trending.py scripts/tests/test_github_trending_source.py scripts/etl/models.py
git commit -m "feat(etl): implement GitHub Trending source with reusable rate limiter"
```

---

### Task 4: Reescribir fuente Hacker News con filtros sólidos

**Files:**
- Create: `scripts/etl/sources/hackernews.py`
- Create: `scripts/tests/test_hackernews_source.py`

**Step 1: Write the failing test**

```python
def test_hn_source_applies_points_and_date_filters():
    items = HackerNewsSource(config=...).fetch()
    assert all(i.points >= 10 for i in items)
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest scripts/tests/test_hackernews_source.py -q`
Expected: FAIL

**Step 3: Implement robust HN source**

Add:
- points filter
- days_back filter
- max stories scan cap
- keyword/domain tech relevance scoring

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest scripts/tests/test_hackernews_source.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/etl/sources/hackernews.py scripts/tests/test_hackernews_source.py
git commit -m "feat(etl): implement Hacker News source with strict quality filters"
```

---

### Task 5: Añadir fuente Google Trends

**Files:**
- Modify: `scripts/requirements.txt`
- Create: `scripts/etl/sources/google_trends.py`
- Create: `scripts/tests/test_google_trends_source.py`
- Modify: `scripts/config.yaml`

**Step 1: Write the failing test**

```python
def test_google_trends_source_returns_topics():
    items = GoogleTrendsSource(config=...).fetch()
    assert isinstance(items, list)
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest scripts/tests/test_google_trends_source.py -q`
Expected: FAIL

**Step 3: Implement Google Trends source**

Add dependency: `pytrends>=4.9.2`.

Implement:
- seed topics from config
- related rising queries
- dedupe + normalize names
- source confidence scoring

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest scripts/tests/test_google_trends_source.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/requirements.txt scripts/etl/sources/google_trends.py scripts/tests/test_google_trends_source.py scripts/config.yaml
git commit -m "feat(etl): add Google Trends ingestion source"
```

---

## Phase 2: Normalización, enriquecimiento y señales

### Task 6: Unificar señales multi-fuente y deduplicación canónica

**Files:**
- Create: `scripts/etl/normalizer.py`
- Create: `scripts/tests/test_normalizer.py`
- Modify: `scripts/etl/models.py`

**Step 1: Write the failing test**

```python
def test_normalizer_merges_same_technology_from_multiple_sources():
    merged = normalize_signals([...])
    assert len([t for t in merged if t.name == "react"]) == 1
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest scripts/tests/test_normalizer.py -q`
Expected: FAIL

**Step 3: Implement normalizer**

Rules:
- case/spacing normalization
- alias map from config (`react.js` -> `react`)
- weighted source score (GitHub/HN/Google)

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest scripts/tests/test_normalizer.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/etl/normalizer.py scripts/tests/test_normalizer.py scripts/etl/models.py
git commit -m "feat(etl): add canonical multi-source normalizer"
```

---

### Task 7: Añadir metadata temporal y scoring de actividad

**Files:**
- Create: `scripts/etl/temporal_analyzer.py`
- Create: `scripts/tests/test_temporal_analyzer.py`
- Modify: `scripts/etl/models.py`

**Step 1: Write the failing test**

```python
def test_temporal_analyzer_returns_trend_and_activity_score():
    analysis = TemporalAnalyzer().analyze(...)
    assert analysis.trend in {"growing", "stable", "declining", "new"}
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest scripts/tests/test_temporal_analyzer.py -q`
Expected: FAIL

**Step 3: Implement temporal analyzer**

Compute:
- recent/new/legacy buckets
- activity score
- trend label
- optional domain breakdown

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest scripts/tests/test_temporal_analyzer.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/etl/temporal_analyzer.py scripts/tests/test_temporal_analyzer.py scripts/etl/models.py
git commit -m "feat(etl): add temporal analysis and trend signals"
```

---

## Phase 3: Clasificación AI y filtrado estratégico

### Task 8: Reescribir clasificador AI robusto con JSON mode

**Files:**
- Create: `scripts/etl/classifier.py`
- Create: `scripts/tests/test_classifier.py`
- Modify: `scripts/config.yaml`

**Step 1: Write the failing test**

```python
def test_classifier_parses_structured_json_response():
    result = classifier.classify_one(...)
    assert result.quadrant in {"platforms", "techniques", "tools", "languages"}
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest scripts/tests/test_classifier.py -q`
Expected: FAIL

**Step 3: Implement classifier**

Requirements:
- `response_format={"type": "json_object"}` when provider supports it
- strict schema validation
- fallback parsing for fenced markdown
- retry with backoff + timeout
- confidence score + rationale field

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest scripts/tests/test_classifier.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/etl/classifier.py scripts/tests/test_classifier.py scripts/config.yaml
git commit -m "feat(etl): implement robust AI classifier with schema validation"
```

---

### Task 9: Implementar AI filter estratégico (high/medium/low)

**Files:**
- Create: `scripts/etl/ai_filter.py`
- Create: `scripts/tests/test_ai_filter.py`
- Modify: `scripts/config.yaml`

**Step 1: Write the failing test**

```python
def test_ai_filter_removes_low_strategic_value_items():
    kept = AITechnologyFilter(...).filter(items)
    assert "rimraf" not in [i.name for i in kept]
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest scripts/tests/test_ai_filter.py -q`
Expected: FAIL

**Step 3: Implement strategic filter pipeline**

Phases:
- auto-ignore rules (utilities/noise)
- AI strategic value evaluation
- include/exclude by config

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest scripts/tests/test_ai_filter.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/etl/ai_filter.py scripts/tests/test_ai_filter.py scripts/config.yaml
git commit -m "feat(etl): add AI strategic filtering to reduce radar noise"
```

---

### Task 10: Detectar duplicados, jerarquías y deprecated

**Files:**
- Modify: `scripts/etl/ai_filter.py`
- Create: `scripts/tests/test_ai_filter_dedupe.py`

**Step 1: Write the failing test**

```python
def test_filter_merges_duplicates_and_flags_deprecated():
    result = filter.apply(...)
    assert "eslint" in result.names
    assert "tslint" not in result.names
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest scripts/tests/test_ai_filter_dedupe.py -q`
Expected: FAIL

**Step 3: Implement dedupe/hierarchy/deprecation phases**

Implement:
- duplicate merge groups (canonical naming)
- parent-child consolidation (e.g. Firebase + subfeatures)
- deprecated map with replacement suggestions

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest scripts/tests/test_ai_filter_dedupe.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/etl/ai_filter.py scripts/tests/test_ai_filter_dedupe.py
git commit -m "feat(etl): add dedupe, hierarchy consolidation and deprecation detection"
```

---

## Phase 4: Priorización baja (pero incluida): deep scan y resiliencia avanzada

### Task 11: Añadir circuit breaker para llamadas AI/API

**Files:**
- Modify: `scripts/etl/rate_limiter.py`
- Create: `scripts/tests/test_circuit_breaker.py`

**Step 1: Write the failing test**

```python
def test_circuit_breaker_opens_after_failures():
    cb = CircuitBreaker(failure_threshold=2, timeout=1)
    with pytest.raises(Exception):
        cb.call(failing_fn)
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest scripts/tests/test_circuit_breaker.py -q`
Expected: FAIL

**Step 3: Implement circuit breaker states**

States:
- CLOSED
- OPEN
- HALF_OPEN

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest scripts/tests/test_circuit_breaker.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/etl/rate_limiter.py scripts/tests/test_circuit_breaker.py
git commit -m "feat(etl): add circuit breaker for resilient external calls"
```

---

### Task 12: Deep scanner opcional para repos de infraestructura

**Files:**
- Create: `scripts/etl/deep_scanner.py`
- Create: `scripts/tests/test_deep_scanner.py`
- Modify: `scripts/config.yaml`

**Step 1: Write the failing test**

```python
def test_deep_scanner_extracts_extra_technologies_from_tree():
    techs = DeepScanner(...).scan_tree("tests/fixtures/tree.txt")
    assert "argocd" in techs
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest scripts/tests/test_deep_scanner.py -q`
Expected: FAIL

**Step 3: Implement deep scanner (low-priority module)**

Implement:
- shallow clone
- tree extraction
- AI tree analysis
- configurable repo allow-list

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest scripts/tests/test_deep_scanner.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/etl/deep_scanner.py scripts/tests/test_deep_scanner.py scripts/config.yaml
git commit -m "feat(etl): add optional deep scanner for infra repository structures"
```

---

## Phase 5: Orquestación final, outputs y compatibilidad

### Task 13: Construir pipeline orquestador completo

**Files:**
- Modify: `scripts/etl/pipeline.py`
- Create: `scripts/tests/test_pipeline_flow.py`

**Step 1: Write the failing test**

```python
def test_pipeline_executes_all_phases_in_order():
    output = RadarPipeline(config=...).run()
    assert "technologies" in output
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest scripts/tests/test_pipeline_flow.py -q`
Expected: FAIL

**Step 3: Implement orchestration flow**

Order:
1. collect source signals
2. normalize + dedupe
3. temporal/domain enrichment
4. classify AI
5. strategic filtering
6. optional deep scan enrich
7. output generation

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest scripts/tests/test_pipeline_flow.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/etl/pipeline.py scripts/tests/test_pipeline_flow.py
git commit -m "feat(etl): orchestrate end-to-end radar pipeline"
```

---

### Task 14: Output dual (public + full) con sanitización

**Files:**
- Create: `scripts/etl/output_generator.py`
- Create: `scripts/tests/test_output_generator.py`
- Modify: `.gitignore`

**Step 1: Write the failing test**

```python
def test_output_generator_creates_sanitized_public_file(tmp_path):
    out = generate_outputs(...)
    assert "repo_names" not in out.public_payload
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest scripts/tests/test_output_generator.py -q`
Expected: FAIL

**Step 3: Implement output generator**

Produce:
- `src/data/data.ai.json` (public)
- `src/data/data.ai.full.json` (internal, gitignored)

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest scripts/tests/test_output_generator.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/etl/output_generator.py scripts/tests/test_output_generator.py .gitignore
git commit -m "feat(etl): generate sanitized and full AI radar outputs"
```

---

### Task 15: Checkpoint/resume para ejecuciones largas

**Files:**
- Create: `scripts/etl/checkpoint.py`
- Create: `scripts/tests/test_checkpoint.py`
- Modify: `scripts/etl/pipeline.py`

**Step 1: Write the failing test**

```python
def test_pipeline_can_resume_from_checkpoint(tmp_path):
    cp = CheckpointStore(tmp_path / "cp.json")
    cp.save({"phase": "classify", "cursor": 20})
    assert cp.load()["phase"] == "classify"
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest scripts/tests/test_checkpoint.py -q`
Expected: FAIL

**Step 3: Implement checkpoint module and pipeline integration**

Features:
- save_interval
- resume flag
- idempotent phase handling

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest scripts/tests/test_checkpoint.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/etl/checkpoint.py scripts/tests/test_checkpoint.py scripts/etl/pipeline.py
git commit -m "feat(etl): add checkpoint and resume support"
```

---

### Task 16: Mantener compatibilidad con `scripts/main.py`

**Files:**
- Modify: `scripts/main.py`
- Create: `scripts/tests/test_main_compat.py`

**Step 1: Write the failing test**

```python
def test_main_calls_new_pipeline_and_writes_output(monkeypatch):
    assert run_main_for_test() == 0
```

**Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest scripts/tests/test_main_compat.py -q`
Expected: FAIL

**Step 3: Rewrite entrypoint with backward-compatible CLI**

Support flags:
- `--resume`
- `--dry-run`
- `--max-technologies`
- `--sources github_trending,hackernews,google_trends`

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest scripts/tests/test_main_compat.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/main.py scripts/tests/test_main_compat.py
git commit -m "refactor(etl): route legacy main entrypoint to new pipeline"
```

---

## Phase 6: CI, validación final y documentación

### Task 17: Actualizar workflow semanal para nuevo ETL

**Files:**
- Modify: `.github/workflows/weekly-update.yml`
- Create: `scripts/tests/test_workflow_contract.py`

**Step 1: Write the failing test**

```python
def test_workflow_uses_expected_secrets_and_commands():
    text = Path(".github/workflows/weekly-update.yml").read_text()
    assert "GH_TOKEN" in text
```

**Step 2: Run test to verify it fails (if contract not met)**

Run: `source .venv/bin/activate && pytest scripts/tests/test_workflow_contract.py -q`
Expected: FAIL or PASS depending on current contract

**Step 3: Update workflow for redesigned ETL**

Include:
- venv setup
- `python scripts/main.py --resume`
- commit only sanitized file

**Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest scripts/tests/test_workflow_contract.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add .github/workflows/weekly-update.yml scripts/tests/test_workflow_contract.py
git commit -m "chore(ci): adapt weekly workflow to redesigned ETL"
```

---

### Task 18: Validación end-to-end + documentación operativa

**Files:**
- Modify: `README.md`
- Create: `docs/etl-architecture.md`
- Create: `docs/etl-ops-runbook.md`

**Step 1: Write the failing validation checklist**

Create checklist doc with required checks:
- sources fetch
- classification quality
- filtering quality
- output integrity

**Step 2: Run complete verification suite**

Run:
- `source .venv/bin/activate && pytest scripts/tests -q`
- `source .venv/bin/activate && python scripts/main.py --dry-run`
- `npm run build`

Expected:
- tests PASS
- dry-run PASS
- frontend build PASS

**Step 3: Update docs for local setup and troubleshooting**

Document:
- required env vars (`GH_TOKEN`, `SYNTHETIC_API_KEY`, `SYNTHETIC_MODEL`)
- source toggles
- resume/checkpoint behavior
- quality guardrails

**Step 4: Final verification**

Run: `git status --short`
Expected: only intended docs/code files changed

**Step 5: Commit**

```bash
git add README.md docs/etl-architecture.md docs/etl-ops-runbook.md
git commit -m "docs(etl): add architecture and operations documentation"
```

---

## Verification Checklist

### Sources
- [ ] GitHub Trending ingestion estable y con rate limit seguro
- [ ] Hacker News filtrado por puntos/fecha funcionando
- [ ] Google Trends integrado y configurable

### Intelligence
- [ ] Clasificador AI retorna JSON válido sin fallback espurio
- [ ] AI filter elimina ruido y consolida duplicados
- [ ] Temporal analyzer calcula trend/activity correctamente

### Reliability
- [ ] Circuit breaker activo en fallos repetidos
- [ ] Checkpoint/resume funcional
- [ ] Workflow semanal estable sin pasos rotos

### Output & Frontend
- [ ] `src/data/data.ai.json` público y sanitizado
- [ ] `src/data/data.ai.full.json` no se commitea
- [ ] Frontend manual/AI mode carga sin romper

---

## Success Criteria

- ✅ ETL modular desacoplado, testeable y mantenible
- ✅ 3 fuentes activas: GitHub Trending, Hacker News y Google Trends
- ✅ Clasificación y filtrado AI con menor ruido y mejor coherencia
- ✅ Re-ejecución segura con resume/checkpoint
- ✅ CI semanal estable y despliegue intacto

---

## Plan Complete

Este plan cubre todas las mejoras detectadas (alta/media/baja prioridad), incluyendo deep scan y resiliencia avanzada, con rediseño completo del ETL y preservando las fuentes que definiste.
