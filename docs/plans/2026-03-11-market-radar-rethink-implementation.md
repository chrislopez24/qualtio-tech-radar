# Market Radar Rethink Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the current ETL with a modular market-snapshot pipeline plus LLM editorial decisions per lane, while preserving the frontend contract at `src/data/data.ai.json`.

**Architecture:** The new flow is `collect -> canonicalize -> score -> lane packs -> lane LLM decisions -> harmonize -> publish`. The old pipeline is removed rather than coexisting behind flags. Internal artifacts become explicit and debuggable; the published output remains stable.

**Tech Stack:** Python ETL, JSON artifacts, lane-based LLM prompts, pytest, existing frontend JSON contract

---

### Task 1: Freeze the current frontend contract

**Files:**
- Inspect: `src/lib/radar-config.ts`
- Inspect: `src/lib/types.ts`
- Inspect: `src/hooks/useRadarData.ts`
- Inspect: `src/data/data.ai.json`
- Create: `scripts/tests/test_radar_contract_v2.py`

**Step 1: Write the failing test**

```python
def test_frontend_contract_fields_remain_supported():
    from pathlib import Path
    import json

    payload = json.loads(Path("src/data/data.ai.json").read_text())

    assert "technologies" in payload
    assert isinstance(payload["technologies"], list)
    for item in payload["technologies"]:
        assert "name" in item
        assert "quadrant" in item
        assert "ring" in item
        assert "description" in item
```

**Step 2: Run test to verify it fails or exposes gaps**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest -s scripts/tests/test_radar_contract_v2.py`
Expected: FAIL until the exact required fields are fully captured.

**Step 3: Expand the test to cover all fields consumed by the frontend**

Add assertions for every field read in:

- `src/lib/radar-config.ts`
- `src/lib/types.ts`
- `src/hooks/useRadarData.ts`

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest -s scripts/tests/test_radar_contract_v2.py`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/tests/test_radar_contract_v2.py
git commit -m "test: lock frontend radar contract"
```

### Task 2: Define the new internal artifact contracts

**Files:**
- Create: `scripts/etl/contracts.py`
- Create: `scripts/tests/test_market_snapshot_contract.py`

**Step 1: Write the failing test**

```python
def test_market_snapshot_entity_contract_is_explicit():
    from etl.contracts import MarketEntity

    entity = MarketEntity(
        canonical_name="React",
        canonical_slug="react",
        editorial_kind="framework",
        topic_family="ui",
    )

    assert entity.canonical_slug == "react"
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest -s scripts/tests/test_market_snapshot_contract.py`
Expected: FAIL because the contract does not exist yet.

**Step 3: Write minimal implementation**

Define typed models for:

- `MarketEntity`
- `LaneEditorialInput`
- `LaneEditorialDecision`
- `EditorialDecisionBundle`

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest -s scripts/tests/test_market_snapshot_contract.py`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/etl/contracts.py scripts/tests/test_market_snapshot_contract.py
git commit -m "feat: define market snapshot and editorial contracts"
```

### Task 3: Build the new module layout and remove dead entry points

**Files:**
- Create: `scripts/etl/discovery/__init__.py`
- Create: `scripts/etl/canonical/__init__.py`
- Create: `scripts/etl/signals/__init__.py`
- Create: `scripts/etl/lanes/__init__.py`
- Create: `scripts/etl/editorial_llm/__init__.py`
- Create: `scripts/etl/publish/__init__.py`
- Modify: `scripts/main.py`
- Test: `scripts/tests/test_etl_imports.py`

**Step 1: Write the failing test**

```python
def test_new_market_radar_modules_are_importable():
    import etl.discovery
    import etl.canonical
    import etl.signals
    import etl.lanes
    import etl.editorial_llm
    import etl.publish
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest -s scripts/tests/test_etl_imports.py -k market_radar_modules`
Expected: FAIL

**Step 3: Create the packages and wire `scripts/main.py` toward the new flow**

Do not implement logic yet; only make the new package structure the official path.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest -s scripts/tests/test_etl_imports.py -k market_radar_modules`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/etl/discovery scripts/etl/canonical scripts/etl/signals scripts/etl/lanes scripts/etl/editorial_llm scripts/etl/publish scripts/main.py scripts/tests/test_etl_imports.py
git commit -m "refactor: scaffold modular market radar pipeline"
```

### Task 4: Implement discovery sources for structured market coverage

**Files:**
- Modify or replace: `scripts/etl/sources/*.py`
- Create: `scripts/etl/discovery/collector.py`
- Create: `scripts/tests/test_discovery_collector.py`

**Step 1: Write the failing test**

```python
def test_discovery_collector_aggregates_records_from_multiple_sources():
    from etl.discovery.collector import DiscoveryCollector

    collector = DiscoveryCollector([])
    assert collector.collect() == []
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest -s scripts/tests/test_discovery_collector.py`
Expected: FAIL

**Step 3: Write minimal implementation**

Collector responsibilities:

- call enabled sources
- return raw records
- tag each record with source metadata
- avoid editorial decisions

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest -s scripts/tests/test_discovery_collector.py`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/etl/discovery/collector.py scripts/tests/test_discovery_collector.py scripts/etl/sources
git commit -m "feat: add market discovery collector"
```

### Task 5: Implement canonical entities and lane assignment

**Files:**
- Create: `scripts/etl/canonical/entities.py`
- Create: `scripts/etl/canonical/resolver.py`
- Create: `scripts/etl/canonical/seeds.py`
- Create: `scripts/tests/test_canonical_resolver_v2.py`

**Step 1: Write the failing test**

```python
def test_canonical_resolver_separates_editorial_kind_from_implementation_context():
    from etl.canonical.resolver import resolve_market_entity

    entity = resolve_market_entity("React", {"ecosystem": "npm"})

    assert entity.editorial_kind == "framework"
    assert "typescript" in entity.implementation_languages or "javascript" in entity.implementation_languages
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest -s scripts/tests/test_canonical_resolver_v2.py`
Expected: FAIL

**Step 3: Write minimal implementation**

Resolver responsibilities:

- alias consolidation
- lane/editorial kind assignment
- implementation context assignment
- seed support for languages/platforms/techniques

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest -s scripts/tests/test_canonical_resolver_v2.py`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/etl/canonical scripts/tests/test_canonical_resolver_v2.py
git commit -m "feat: add canonical market entity resolver"
```

### Task 6: Build the market snapshot and signal engine

**Files:**
- Create: `scripts/etl/signals/scoring.py`
- Create: `scripts/etl/signals/snapshot_builder.py`
- Create: `scripts/tests/test_snapshot_builder.py`

**Step 1: Write the failing test**

```python
def test_snapshot_builder_produces_entities_with_adoption_and_momentum():
    from etl.signals.snapshot_builder import build_market_snapshot

    snapshot = build_market_snapshot([])
    assert snapshot == []
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest -s scripts/tests/test_snapshot_builder.py`
Expected: FAIL

**Step 3: Write minimal implementation**

Compute simple, explicit features:

- adoption
- momentum
- maturity
- breadth
- stability
- risk

No rings here.

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest -s scripts/tests/test_snapshot_builder.py`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/etl/signals scripts/tests/test_snapshot_builder.py
git commit -m "feat: build market snapshot and signal scoring"
```

### Task 7: Build lane packs for efficient LLM calls

**Files:**
- Create: `scripts/etl/lanes/packer.py`
- Create: `scripts/tests/test_lane_packer.py`

**Step 1: Write the failing test**

```python
def test_lane_packer_groups_snapshot_entities_by_lane():
    from etl.lanes.packer import pack_lanes

    packed = pack_lanes([])
    assert set(packed.keys()) == {"languages", "frameworks", "tools", "platforms", "techniques"}
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest -s scripts/tests/test_lane_packer.py`
Expected: FAIL

**Step 3: Write minimal implementation**

Each lane pack should contain:

- candidate entities
- compact feature summaries
- nearby alternatives
- prompt-safe context

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest -s scripts/tests/test_lane_packer.py`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/etl/lanes/packer.py scripts/tests/test_lane_packer.py
git commit -m "feat: pack market snapshot into editorial lanes"
```

### Task 8: Implement lane editorial LLM decisions

**Files:**
- Create: `scripts/etl/editorial_llm/lane_editor.py`
- Create: `scripts/etl/editorial_llm/prompts.py`
- Create: `scripts/tests/test_lane_editor.py`

**Step 1: Write the failing test**

```python
def test_lane_editor_parses_editorial_decisions_from_llm_output():
    from etl.editorial_llm.lane_editor import parse_lane_decision

    payload = parse_lane_decision({
        "lane": "frameworks",
        "included": [],
        "excluded": [],
    })

    assert payload.lane == "frameworks"
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest -s scripts/tests/test_lane_editor.py`
Expected: FAIL

**Step 3: Write minimal implementation**

Requirements:

- one decision call per lane
- strict JSON output
- include/exclude/ring/definition/thesis fields
- retry or fail cleanly on invalid JSON

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest -s scripts/tests/test_lane_editor.py`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/etl/editorial_llm scripts/tests/test_lane_editor.py
git commit -m "feat: add lane-based editorial llm decisions"
```

### Task 9: Implement global harmonization and publishing

**Files:**
- Create: `scripts/etl/editorial_llm/harmonizer.py`
- Create: `scripts/etl/publish/publisher.py`
- Modify: `scripts/main.py`
- Create: `scripts/tests/test_publisher_v2.py`

**Step 1: Write the failing test**

```python
def test_publisher_writes_frontend_contract_from_editorial_decision(tmp_path):
    from etl.publish.publisher import publish_radar

    result = publish_radar({"blips": []}, tmp_path / "data.ai.json")
    assert result["technologies"] == []
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest -s scripts/tests/test_publisher_v2.py`
Expected: FAIL

**Step 3: Write minimal implementation**

Responsibilities:

- harmonize lane decisions
- map final decisions to `data.ai.json`
- preserve frontend field names
- reject invalid final outputs

**Step 4: Run test to verify it passes**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest -s scripts/tests/test_publisher_v2.py`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts/etl/editorial_llm/harmonizer.py scripts/etl/publish/publisher.py scripts/main.py scripts/tests/test_publisher_v2.py
git commit -m "feat: publish radar from lane editorial decisions"
```

### Task 10: Replace the old pipeline and delete dead code

**Files:**
- Remove obsolete ETL modules and tests that no longer fit the new architecture
- Modify: `docs/etl-ops-runbook.md`
- Modify: `docs/radar-review-checklist.md`
- Create: `scripts/tests/test_cleanup_contract.py`

**Step 1: Write the failing test**

```python
def test_obsolete_pipeline_modules_are_not_imported_by_main():
    from pathlib import Path

    content = Path("scripts/main.py").read_text()
    assert "RadarPipeline" not in content
```

**Step 2: Run test to verify it fails**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest -s scripts/tests/test_cleanup_contract.py`
Expected: FAIL

**Step 3: Remove dead code and update docs**

Clean up:

- obsolete pipeline orchestration
- dead config keys
- dead tests
- no-longer-used artifacts

Keep only code needed by the new architecture.

**Step 4: Run focused tests to verify cleanup**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest -s scripts/tests/test_cleanup_contract.py scripts/tests/test_radar_contract_v2.py scripts/tests/test_publisher_v2.py`
Expected: PASS

**Step 5: Commit**

```bash
git add scripts docs
git commit -m "refactor: replace legacy pipeline with modular market radar flow"
```

### Task 11: Run end-to-end verification on real data

**Files:**
- Run against: `scripts/main.py`
- Verify: `src/data/data.ai.json`
- Verify: generated lane/editorial artifacts

**Step 1: Run the full pipeline**

Run: `PYTHONPATH=scripts ./.venv/bin/python scripts/main.py`
Expected: exit 0 and write `src/data/data.ai.json`

**Step 2: Validate the final artifact**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest -s scripts/tests/test_radar_contract_v2.py scripts/tests/test_publisher_v2.py`
Expected: PASS

**Step 3: Review output quality**

Check:

- the radar has coherent blips
- each blip has a definition
- each blip has a thesis
- no duplicates across lanes
- the result feels market-aware rather than repo-trending-only

**Step 4: Run the whole relevant test slice**

Run: `PYTHONPATH=scripts ./.venv/bin/pytest -s scripts/tests`
Expected: PASS, or a clearly documented set of intentional removals/replacements

**Step 5: Commit**

```bash
git add src/data/data.ai.json
git commit -m "test: verify modular market radar end to end"
```

Plan complete and saved to `docs/plans/2026-03-11-market-radar-rethink-implementation.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
