# Market-Faithful Radar Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Harden the ETL so the radar publishes semantically correct quadrants, evidence-backed provenance, honest quality signals, and ring-balanced output without letting the LLM own the final artifact.

**Architecture:** Keep the current ETL entrypoint and deterministic market/ring policy, but refactor the classifier and post-processing contract so the LLM only contributes constrained semantic fields. Enforce evidence and quadrant invariants in code, then expose the resulting overrides, weak items, and ring-fill behavior through pipeline metadata, review summaries, and shadow gating.

**Tech Stack:** Python ETL in `scripts/etl`, pytest in `scripts/tests`, YAML config in `scripts/config.yaml`, JSON artifact generation in `scripts/etl/pipeline.py` and `scripts/etl/output_generator.py`

---

### Task 1: Lock quadrant semantics with hard rules and regression tests

**Files:**
- Create: `scripts/tests/test_quadrant_logic.py`
- Modify: `scripts/etl/quadrant_logic.py`
- Modify: `scripts/tests/test_classifier.py`

**Step 1: Write the failing test**

```python
from types import SimpleNamespace

from etl.quadrant_logic import infer_quadrant


def _tech(name: str, description: str, language: str = "", topics: list[str] | None = None):
    return SimpleNamespace(name=name, description=description, language=language, topics=topics or [])


def test_infer_quadrant_keeps_languages_only_for_real_languages():
    assert infer_quadrant(_tech("TypeScript", "Typed programming language", "TypeScript")) == "languages"
    assert infer_quadrant(_tech("PyTorch", "Deep learning framework for Python", "Python", ["framework", "machine-learning"])) == "tools"
    assert infer_quadrant(_tech("open-webui", "Self-hosted AI chat interface and tool", "Python", ["ui", "tool"])) == "tools"
    assert infer_quadrant(_tech("youtube-dl", "Command-line video downloader", "Python", ["cli", "tool"])) == "tools"
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest scripts/tests/test_quadrant_logic.py -q`

Expected: FAIL because the current heuristics let language metadata and loose keywords override artifact type too easily.

**Step 3: Write minimal implementation**

```python
KNOWN_LANGUAGES = {"python", "javascript", "typescript", "rust", "go", "java", "c#", "kotlin", "swift", "php", "ruby"}
TOOL_KEYWORDS = {"tool", "cli", "framework", "library", "sdk", "plugin", "extension", "ui", "interface"}


def infer_quadrant(tech: Any) -> str:
    name = str(getattr(tech, "name", "") or "").lower()
    description = str(getattr(tech, "description", "") or "").lower()
    language = str(getattr(tech, "language", "") or "").lower()
    topics = {str(topic).lower() for topic in getattr(tech, "topics", [])}
    text = f"{name} {description}"

    if name in KNOWN_LANGUAGES or "programming language" in text or (language in KNOWN_LANGUAGES and "language" in text):
        return "languages"
    if any(keyword in text for keyword in TOOL_KEYWORDS) or topics & {"tool", "framework", "library", "cli"}:
        return "tools"
    ...
```

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest scripts/tests/test_quadrant_logic.py scripts/tests/test_classifier.py -q -k 'quadrant or validates_quadrant'`

Expected: PASS

**Step 5: Commit**

```bash
git add scripts/etl/quadrant_logic.py scripts/tests/test_quadrant_logic.py scripts/tests/test_classifier.py
git commit -m "fix: harden quadrant semantics for radar artifacts"
```

### Task 2: Reduce the classifier to constrained semantic output

**Files:**
- Modify: `scripts/etl/classifier.py`
- Modify: `scripts/etl/pipeline.py`
- Modify: `scripts/tests/test_classifier.py`
- Modify: `scripts/tests/test_pipeline_flow.py`

**Step 1: Write the failing test**

```python
def test_classifier_ignores_llm_ring_and_keeps_semantic_fields_only():
    classifier = TechnologyClassifier(api_key="test-key")
    result = classifier._parse_response(
        '{"name":"PyTorch","quadrant":"languages","description":"Deep learning framework","confidence":0.82,"trend":"up","rationale":"Popular ML framework","strategic_value":"high","suspicion_flags":["quadrant_mismatch"]}',
        "PyTorch",
    )

    assert result.quadrant == "languages"
    assert result.description == "Deep learning framework"
    assert result.ring == "trial"
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest scripts/tests/test_classifier.py -q -k 'semantic_fields_only or strategic_value'`

Expected: FAIL because the parser still treats ring as LLM-owned output.

**Step 3: Write minimal implementation**

```python
@dataclass
class ClassificationResult:
    name: str
    quadrant: str
    ring: str = "trial"
    description: str = ""
    confidence: float = 0.5
    trend: str = "stable"
    rationale: str = ""
    strategic_value: str = "medium"
    suspicion_flags: list[str] = field(default_factory=list)


class ClassificationSchema(BaseModel):
    name: str
    quadrant: str
    description: str
    confidence: float
    trend: str
    rationale: str | None = None
    strategic_value: str = "medium"
    suspicion_flags: list[str] = Field(default_factory=list)
```

- Update `SYSTEM_PROMPT` so it asks for semantic quadrant, description, confidence, trend, rationale, strategic value, and suspicion flags only.
- Keep deterministic ring assignment in `scripts/etl/pipeline.py::_assign_market_rings`.
- Preserve backward compatibility by defaulting `ring` in parsed results until all call sites are updated.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest scripts/tests/test_classifier.py scripts/tests/test_pipeline_flow.py -q -k 'semantic or classification_model or strategic_value'`

Expected: PASS

**Step 5: Commit**

```bash
git add scripts/etl/classifier.py scripts/etl/pipeline.py scripts/tests/test_classifier.py scripts/tests/test_pipeline_flow.py
git commit -m "refactor: constrain llm classification to semantic output"
```

### Task 3: Enforce evidence invariants before publication

**Files:**
- Modify: `scripts/etl/pipeline.py`
- Modify: `scripts/etl/output_generator.py`
- Modify: `scripts/tests/test_output_generator.py`
- Modify: `scripts/tests/test_pipeline_flow.py`

**Step 1: Write the failing test**

```python
def test_output_marks_item_invalid_when_source_coverage_has_no_evidence():
    from types import SimpleNamespace
    from etl.pipeline import RadarPipeline

    pipeline = RadarPipeline()
    output = pipeline._generate_output([
        SimpleNamespace(
            name="Python",
            description="Programming language",
            stars=0,
            quadrant="languages",
            ring="adopt",
            confidence=0.9,
            trend="stable",
            moved=0,
            market_score=85.0,
            signals={"gh_momentum": 50.0, "gh_popularity": 70.0, "hn_heat": 0.0, "source_coverage": 2.0},
            evidence=[],
            is_deprecated=False,
            replacement=None,
        )
    ])

    tech = output["technologies"][0]
    assert tech["editorialStatus"] == "invalid"
    assert "missingEvidence" in tech["editorialFlags"]
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest scripts/tests/test_output_generator.py -q -k 'missing_evidence or source_coverage'`

Expected: FAIL because the current serializer emits coverage and summary even when `evidence[]` is absent.

**Step 3: Write minimal implementation**

```python
def _editorial_flags(raw_signals: dict[str, Any], evidence: list[EvidenceRecord]) -> tuple[str, list[str]]:
    flags: list[str] = []
    source_coverage = _source_coverage(raw_signals, evidence)
    if source_coverage > 0 and not evidence:
        flags.append("missingEvidence")
    status = "invalid" if "missingEvidence" in flags else "clean"
    return status, flags
```

- Add `editorialStatus` and `editorialFlags` to serialized technologies.
- Ensure `whyThisRing` and quality summaries consume the corrected status instead of assuming coverage is trustworthy.
- Keep `sanitize_for_public()` passing these fields through.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest scripts/tests/test_output_generator.py scripts/tests/test_pipeline_flow.py -q -k 'missing_evidence or explainability or compact_explainability_metadata'`

Expected: PASS

**Step 5: Commit**

```bash
git add scripts/etl/pipeline.py scripts/etl/output_generator.py scripts/tests/test_output_generator.py scripts/tests/test_pipeline_flow.py
git commit -m "fix: enforce radar evidence publication invariants"
```

### Task 4: Penalize semantic overrides and evidence failures in aggregate quality

**Files:**
- Modify: `scripts/etl/artifact_quality.py`
- Modify: `scripts/tests/test_output_generator.py`

**Step 1: Write the failing test**

```python
def test_quality_snapshot_counts_quadrant_mismatch_and_missing_evidence_as_editorially_weak():
    from etl.artifact_quality import quality_snapshot

    snapshot = quality_snapshot([
        {
            "id": "pytorch",
            "name": "PyTorch",
            "quadrant": "languages",
            "ring": "trial",
            "description": "Deep learning framework",
            "marketScore": 82.3,
            "sourceCoverage": 2,
            "editorialStatus": "invalid",
            "editorialFlags": ["quadrantMismatch", "missingEvidence"],
        }
    ], strong_ring="trial")

    assert snapshot["editoriallyWeakCount"] == 1
    assert snapshot["topSuspicious"][0]["reasons"] == ["quadrantMismatch", "missingEvidence"]
    assert snapshot["status"] == "bad"
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest scripts/tests/test_output_generator.py -q -k 'quadrant_mismatch and editorally'`

Expected: FAIL because `quality_snapshot()` only counts GitHub-only/resource/editorial ring weakness today.

**Step 3: Write minimal implementation**

```python
editorial_flags = [str(flag) for flag in entry.get("editorialFlags", []) if flag]
if editorial_flags:
    editorially_weak_count += 1
    reasons.extend(editorial_flags)
if str(entry.get("editorialStatus", "")) == "invalid":
    status = "bad"
```

- Preserve existing GitHub-only and resource-like logic.
- Merge new reasons into `topSuspicious` without losing current signals.
- Ensure quadrant and quadrant-ring snapshots inherit the same stricter logic.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest scripts/tests/test_output_generator.py -q -k 'quality_data_for_each_ring or educational_trial or quadrant_mismatch'`

Expected: PASS

**Step 5: Commit**

```bash
git add scripts/etl/artifact_quality.py scripts/tests/test_output_generator.py
git commit -m "fix: make radar quality snapshots penalize semantic failures"
```

### Task 5: Add soft per-ring targets and controlled underfill behavior

**Files:**
- Modify: `scripts/etl/config.py`
- Modify: `scripts/config.yaml`
- Modify: `scripts/etl/selection_logic.py`
- Modify: `scripts/etl/pipeline.py`
- Modify: `scripts/tests/test_pipeline_flow.py`

**Step 1: Write the failing test**

```python
def test_strategic_filter_prefers_soft_ring_targets_without_using_invalid_items():
    from etl.config import ETLConfig

    config = ETLConfig()
    config.distribution.target_total = 40
    config.distribution.min_per_ring = 8
    config.distribution.target_per_ring = 10
    config.distribution.max_per_ring = 15

    ...
    assert output_meta["ringFillStatus"]["hold"]["underfilled"] is True
    assert output_meta["ringDistribution"]["hold"] < 10
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest scripts/tests/test_pipeline_flow.py -q -k 'ring_targets or underfill'`

Expected: FAIL because selection currently balances quadrants only and does not expose ring fill status.

**Step 3: Write minimal implementation**

```python
class DistributionConfig(BaseModel):
    target_total: int = Field(ge=5, default=40)
    min_per_quadrant: int = Field(ge=1, default=2)
    max_per_quadrant: int = Field(ge=1, default=12)
    min_per_ring: int = Field(ge=0, default=8)
    target_per_ring: int = Field(ge=0, default=10)
    max_per_ring: int = Field(ge=0, default=15)
```

- Update `strategic_filter()` to select by quality first, then attempt ring balancing within quadrant limits.
- Do not select `editorialStatus == "invalid"` items to satisfy ring targets.
- Emit `ringFillStatus` and `underfilledRings` in pipeline metadata.
- Keep underfill explicit rather than silently padding weak rings.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest scripts/tests/test_pipeline_flow.py scripts/tests/test_output_generator.py -q -k 'ringDistribution or ring_targets or underfill'`

Expected: PASS

**Step 5: Commit**

```bash
git add scripts/etl/config.py scripts/config.yaml scripts/etl/selection_logic.py scripts/etl/pipeline.py scripts/tests/test_pipeline_flow.py scripts/tests/test_output_generator.py
git commit -m "feat: add soft per-ring radar selection targets"
```

### Task 6: Extend review and shadow gates with semantic and evidence failures

**Files:**
- Modify: `scripts/etl/shadow_eval.py`
- Modify: `scripts/review_radar_output.py`
- Modify: `scripts/tests/test_shadow_eval.py`
- Modify: `scripts/tests/test_review_radar_output.py`

**Step 1: Write the failing test**

```python
def test_shadow_eval_flags_missing_evidence_and_quadrant_override_failures():
    from etl.shadow_eval import compare_outputs

    optimized = {
        "technologies": [
            {
                "id": "pytorch",
                "ring": "trial",
                "quadrant": "tools",
                "sourceCoverage": 2,
                "editorialStatus": "invalid",
                "editorialFlags": ["quadrantMismatch", "missingEvidence"],
            }
        ]
    }

    report = compare_outputs({"technologies": []}, optimized)
    assert report["missing_evidence_count"] == 1
    assert report["quadrant_override_count"] == 1
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest scripts/tests/test_shadow_eval.py scripts/tests/test_review_radar_output.py -q -k 'missing_evidence or quadrant_override'`

Expected: FAIL because the current report only tracks overlap and GitHub-bias style signals.

**Step 3: Write minimal implementation**

```python
def _count_editorial_flags(entries: list[dict[str, Any]]) -> dict[str, int]:
    missing_evidence = 0
    quadrant_override = 0
    for entry in entries:
        flags = {str(flag) for flag in entry.get("editorialFlags", [])}
        missing_evidence += int("missingEvidence" in flags)
        quadrant_override += int("quadrantMismatch" in flags)
    return {
        "missing_evidence_count": missing_evidence,
        "quadrant_override_count": quadrant_override,
    }
```

- Merge these counts into `compare_outputs()`.
- Surface them in `build_review_summary()` under suspicious items and publish readiness.
- Update `classify_quality_gate()` so severe evidence failures force `fail`.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest scripts/tests/test_shadow_eval.py scripts/tests/test_review_radar_output.py -q`

Expected: PASS

**Step 5: Commit**

```bash
git add scripts/etl/shadow_eval.py scripts/review_radar_output.py scripts/tests/test_shadow_eval.py scripts/tests/test_review_radar_output.py
git commit -m "feat: extend radar gates with semantic and evidence failures"
```

### Task 7: Verify the end-to-end contract and document rollout defaults

**Files:**
- Modify: `README.md`
- Modify: `scripts/config.yaml`
- Modify: `scripts/tests/test_output_generator.py`
- Modify: `scripts/tests/test_main_compat.py`

**Step 1: Write the failing test**

```python
def test_main_defaults_support_market_faithful_base_radar_targets():
    config = load_etl_config("scripts/config.yaml")
    assert config.distribution.target_per_ring == 10
    assert config.distribution.max_per_ring == 15
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest scripts/tests/test_main_compat.py scripts/tests/test_output_generator.py -q -k 'market_faithful or ringFillStatus'`

Expected: FAIL until config defaults and emitted metadata are aligned.

**Step 3: Write minimal implementation**

```yaml
distribution:
  target_total: 40
  min_per_quadrant: 2
  max_per_quadrant: 12
  min_per_ring: 8
  target_per_ring: 10
  max_per_ring: 15
```

- Update `README.md` so the pipeline contract explains deterministic rings, constrained LLM semantics, evidence invariants, and ring-fill behavior.
- Keep config language explicit that `15` per ring is opportunistic, not guaranteed.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest scripts/tests/test_main_compat.py scripts/tests/test_output_generator.py -q`

Expected: PASS

**Step 5: Run the focused regression suite**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest scripts/tests/test_quadrant_logic.py scripts/tests/test_classifier.py scripts/tests/test_output_generator.py scripts/tests/test_pipeline_flow.py scripts/tests/test_shadow_eval.py scripts/tests/test_review_radar_output.py scripts/tests/test_main_compat.py -q`

Expected: PASS

**Step 6: Commit**

```bash
git add README.md scripts/config.yaml scripts/tests/test_main_compat.py scripts/tests/test_output_generator.py
git commit -m "docs: align radar defaults with market-faithful contract"
```

## Rollout Notes

- Start with the strict evidence and quadrant changes before making shadow gate failures hard in automation.
- Validate the new ring-fill behavior against a few real snapshots before treating `40` as mandatory.
- If the candidate pool cannot sustain `10` per ring, prefer explicit underfill over synthetic promotion.

## Verification Checklist

- Run the focused pytest commands in each task.
- Run one full pipeline execution after Task 6: `PYTHONPATH=scripts ./.venv/bin/python scripts/main.py --shadow`
- Inspect `src/data/data.ai.json` for corrected quadrant placement, atomic evidence, and `meta.pipeline.ringFillStatus`.
- Inspect `artifacts/shadow_eval.json` for missing-evidence and quadrant-override counts.

## Git Notes

- The commit steps above are part of the implementation workflow, but this plan file itself is intentionally not committed because no commit was requested in-session.
