# Scripts Cleanup (Aggressive) Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Consolidate ETL runtime to active `scripts/etl` modules, generate only `src/data/data.ai.json`, and prevent placeholder descriptions from reaching output.

**Architecture:** The pipeline remains phase-based but enforces a hard description-quality gate before output. Legacy runtime paths under `scripts/ai` and `scripts/scraper` are removed after source/classifier wiring is fully migrated to ETL-native modules. Output contract is simplified to one public JSON file with deterministic validation tests.

**Tech Stack:** Python 3.12, pytest, requests/httpx, Pydantic, GitHub Actions.

---

### Task 1: Reproduce and lock the classifier `NoneType.strip` bug

**Files:**
- Modify: `scripts/tests/test_classifier.py`
- Modify: `scripts/etl/classifier.py`

**Step 1: Write the failing test**

```python
def test_classifier_handles_none_content_from_llm():
    classifier = TechnologyClassifier(api_key="test-key")
    result = classifier._parse_response(None, "React")
    assert result.name == "React"
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="scripts" .venv/bin/pytest scripts/tests/test_classifier.py::test_classifier_handles_none_content_from_llm -q`
Expected: FAIL with `'NoneType' object has no attribute 'strip'`.

**Step 3: Write minimal implementation**

```python
def _extract_json(self, content):
    if not content:
        return None
    content = content.strip()
    ...
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH="scripts" .venv/bin/pytest scripts/tests/test_classifier.py::test_classifier_handles_none_content_from_llm -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/tests/test_classifier.py scripts/etl/classifier.py
git commit -m "fix: handle empty LLM content in classifier parsing"
```

### Task 2: Add description-quality gate and block placeholders

**Files:**
- Create: `scripts/etl/description_quality.py`
- Create: `scripts/tests/test_description_quality.py`

**Step 1: Write the failing test**

```python
def test_rejects_placeholder_description_pattern():
    assert not is_valid_description("awesome-python - technology with 0 stars")

def test_accepts_real_description():
    assert is_valid_description("Popular curated list of Python frameworks and tools")
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="scripts" .venv/bin/pytest scripts/tests/test_description_quality.py -q`
Expected: FAIL because module/function does not exist.

**Step 3: Write minimal implementation**

```python
PLACEHOLDER_PATTERNS = [
    re.compile(r"-\s*technology\s+with\s+\d+\s+stars", re.I),
]

def is_valid_description(text: str | None) -> bool:
    if not text or not text.strip():
        return False
    if any(p.search(text) for p in PLACEHOLDER_PATTERNS):
        return False
    return True
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH="scripts" .venv/bin/pytest scripts/tests/test_description_quality.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/etl/description_quality.py scripts/tests/test_description_quality.py
git commit -m "feat: add description quality validator for ETL output"
```

### Task 3: Enforce quality gate in pipeline and drop bad entries

**Files:**
- Modify: `scripts/etl/pipeline.py`
- Modify: `scripts/tests/test_pipeline_flow.py`

**Step 1: Write the failing test**

```python
def test_pipeline_drops_items_with_placeholder_descriptions(...):
    # one valid + one placeholder
    # run strategic/output phase
    assert "awesome-python" not in output_ids
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="scripts" .venv/bin/pytest scripts/tests/test_pipeline_flow.py::test_pipeline_drops_items_with_placeholder_descriptions -q`
Expected: FAIL because placeholder item is still present.

**Step 3: Write minimal implementation**

```python
from etl.description_quality import is_valid_description

if not is_valid_description(classification.description):
    dropped_bad_description += 1
    continue
```

Add phase log with dropped count.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH="scripts" .venv/bin/pytest scripts/tests/test_pipeline_flow.py::test_pipeline_drops_items_with_placeholder_descriptions -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/etl/pipeline.py scripts/tests/test_pipeline_flow.py
git commit -m "fix: exclude technologies with placeholder descriptions"
```

### Task 4: Move to single output file (`data.ai.json` only)

**Files:**
- Modify: `scripts/main.py`
- Modify: `scripts/etl/config.py`
- Modify: `scripts/config.yaml`
- Modify: `scripts/etl/output_generator.py`
- Modify: `scripts/tests/test_main_compat.py`
- Modify: `scripts/tests/test_output_generator.py`

**Step 1: Write the failing test**

```python
def test_main_writes_only_public_output(tmp_path):
    assert public_file.exists()
    assert not full_file.exists()
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="scripts" .venv/bin/pytest scripts/tests/test_main_compat.py::test_main_writes_only_public_output -q`
Expected: FAIL because full file is still created.

**Step 3: Write minimal implementation**

```python
# remove internal_file from config contract
# write only config.output.public_file
```

**Step 4: Run tests to verify they pass**

Run: `PYTHONPATH="scripts" .venv/bin/pytest scripts/tests/test_main_compat.py scripts/tests/test_output_generator.py -q`
Expected: PASS with updated assertions.

**Step 5: Commit**

```bash
git add scripts/main.py scripts/etl/config.py scripts/config.yaml scripts/etl/output_generator.py scripts/tests/test_main_compat.py scripts/tests/test_output_generator.py
git commit -m "refactor: switch ETL to single public output file"
```

### Task 5: Consolidate source/runtime imports to ETL-native modules

**Files:**
- Modify: `scripts/etl/pipeline.py`
- Modify: `scripts/etl/sources/github_trending.py`
- Modify: `scripts/tests/test_etl_imports.py`
- Modify: `scripts/tests/test_pipeline_flow.py`

**Step 1: Write the failing test**

```python
def test_pipeline_does_not_import_legacy_scraper_modules():
    import etl.pipeline as p
    assert "scraper." not in p.__file__  # replace with concrete import assertions
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH="scripts" .venv/bin/pytest scripts/tests/test_etl_imports.py -q`
Expected: FAIL due legacy import references.

**Step 3: Write minimal implementation**

```python
# pipeline pulls from etl.sources.github_trending / etl.sources.hackernews
# remove direct runtime dependency on scraper.* in pipeline path
```

**Step 4: Run tests to verify they pass**

Run: `PYTHONPATH="scripts" .venv/bin/pytest scripts/tests/test_etl_imports.py scripts/tests/test_pipeline_flow.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/etl/pipeline.py scripts/etl/sources/github_trending.py scripts/tests/test_etl_imports.py scripts/tests/test_pipeline_flow.py
git commit -m "refactor: remove legacy scraper imports from ETL runtime"
```

### Task 6: Remove dead files and update docs/workflow contract

**Files:**
- Delete: `scripts/ai/classifier.py`
- Delete: `scripts/scraper/github.py`
- Delete: `scripts/scraper/github_scraper.py`
- Delete: `scripts/scraper/hackernews.py`
- Modify: `.github/workflows/weekly-update.yml`
- Modify: `docs/etl-architecture.md`
- Modify: `docs/etl-ops-runbook.md`

**Step 1: Write failing contract test**

```python
def test_workflow_tracks_single_output_file():
    text = Path(".github/workflows/weekly-update.yml").read_text()
    assert "src/data/data.ai.json" in text
    assert "data.ai.full.json" not in text
```

**Step 2: Run test to verify it fails (if workflow/docs stale)**

Run: `PYTHONPATH="scripts" .venv/bin/pytest scripts/tests/test_workflow_contract.py -q`
Expected: FAIL until workflow/docs are aligned.

**Step 3: Apply minimal cleanup implementation**

```python
# remove dead modules after references are gone
# update docs to single-file output contract
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH="scripts" .venv/bin/pytest scripts/tests/test_workflow_contract.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add .github/workflows/weekly-update.yml docs/etl-architecture.md docs/etl-ops-runbook.md scripts/tests/test_workflow_contract.py
git rm scripts/ai/classifier.py scripts/scraper/github.py scripts/scraper/github_scraper.py scripts/scraper/hackernews.py
git commit -m "chore: remove legacy scripts and align docs/workflow with ETL"
```

### Task 7: Full verification on master (no worktrees)

**Files:**
- Verify: `scripts/tests/*`
- Verify: `src/data/data.ai.json`

**Step 1: Run focused ETL test suite**

Run:

```bash
PYTHONPATH="scripts" .venv/bin/pytest scripts/tests/test_classifier.py scripts/tests/test_description_quality.py scripts/tests/test_pipeline_flow.py scripts/tests/test_main_compat.py scripts/tests/test_output_generator.py scripts/tests/test_workflow_contract.py -q
```

Expected: all passing.

**Step 2: Run local ETL smoke execution**

Run:

```bash
PYTHONUNBUFFERED=1 .venv/bin/python -u scripts/main.py --sources github_trending > etl-smoke.log 2>&1
```

Expected: process completes and writes `src/data/data.ai.json`.

**Step 3: Validate output quality contract**

Run:

```bash
.venv/bin/python - <<'PY'
import json, re
payload = json.load(open('src/data/data.ai.json'))
bad = [t['name'] for t in payload.get('technologies', []) if re.search(r'-\s*technology\s+with\s+\d+\s+stars', (t.get('description') or ''), re.I)]
assert not bad, bad
print('quality-ok', len(payload.get('technologies', [])))
PY
```

Expected: `quality-ok ...` and no assertion failure.

**Step 4: Final commit**

```bash
git add docs/plans/2026-02-24-scripts-cleanup-design.md docs/plans/2026-02-24-scripts-cleanup-implementation-plan.md
git commit -m "docs: add scripts cleanup design and execution plan"
```
