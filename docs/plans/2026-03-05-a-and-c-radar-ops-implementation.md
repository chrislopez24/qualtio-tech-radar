# A+C Radar Ops Hardening Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement track A (operational explainability + "what changed" visibility + provenance) and track C (baseline-state hardening + workflow performance + ETL complexity reduction) without changing business behavior or lowering quality thresholds.

**Architecture:** Extend existing shadow-eval outputs into first-class operational state surfaced in ETL artifacts and frontend panels, while preserving strict gate policy. Refactor ETL internals into clearer layered functions (metrics, policy, report) and harden CI workflow with dependency caching and deterministic data-source safeguards. Keep output compatibility by adding optional fields only.

**Tech Stack:** Python ETL + Pytest, GitHub Actions YAML, Next.js/React/TypeScript + Vitest.

---

### Task 1: Add explicit leader transition explainability fields (A)

**Files:**
- Modify: `scripts/etl/shadow_eval.py`
- Test: `scripts/tests/test_shadow_eval.py`

**Step 1: Write failing tests for explainability payload**

Add tests asserting report contains:
- `leader_transition_summary` with candidate/promoted counts
- per-candidate details including `leader_id`, `change_type`, `consecutive_count`
- a human-readable `next_action`

**Step 2: Run targeted test to verify failure**

Run: `python3 -m pytest scripts/tests/test_shadow_eval.py -q`
Expected: FAIL for new explainability expectations.

**Step 3: Implement minimal report augmentation**

In `scripts/etl/shadow_eval.py`:
- keep strict gate semantics unchanged
- enrich output fields from current leader state into a stable structure

**Step 4: Re-run targeted tests**

Run: `python3 -m pytest scripts/tests/test_shadow_eval.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/etl/shadow_eval.py scripts/tests/test_shadow_eval.py
git commit -m "feat(etl): expose leader transition explainability in shadow reports"
```

---

### Task 2: Add "What changed?" payload contract for UI consumption (A)

**Files:**
- Modify: `scripts/main.py`
- Modify: `src/lib/types.ts`
- Test: `scripts/tests/test_main_compat.py`
- Test: `src/lib/radar-data-schema.test.ts`

**Step 1: Write failing tests for meta.shadowGate contract**

Add tests validating `meta.shadowGate` includes:
- `status`, `nextAction`
- `filteredCount`, `addedCount`
- `filteredSample`
- `candidateChanges`

**Step 2: Run targeted tests to verify failure**

Run:
- `python3 -m pytest scripts/tests/test_main_compat.py -q`
- `npm test -- src/lib/radar-data-schema.test.ts`
Expected: FAIL at first.

**Step 3: Implement minimal contract wiring**

In `scripts/main.py` shadow summary builder:
- normalize keys and ensure optional-but-stable shape
In `src/lib/types.ts`:
- extend optional typing for new shadow fields

**Step 4: Re-run targeted tests**

Run:
- `python3 -m pytest scripts/tests/test_main_compat.py -q`
- `npm test -- src/lib/radar-data-schema.test.ts`
Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/main.py src/lib/types.ts scripts/tests/test_main_compat.py src/lib/radar-data-schema.test.ts
git commit -m "feat(data): add stable what-changed shadow metadata contract"
```

---

### Task 3: Surface "What changed" + leader-candidate status in frontend (A)

**Files:**
- Modify: `src/components/WatchlistPanel.tsx`
- Modify: `src/components/DetailPanel.tsx`
- Modify: `src/components/WatchlistPanel.test.tsx`
- Modify: `src/components/DetailPanel.test.tsx`

**Step 1: Write failing UI tests**

Add tests for rendering:
- shadow status badge (`pass|warn|fail`)
- added/filtered counters
- candidate transition summary text

**Step 2: Run focused tests to verify failure**

Run:
- `npm test -- src/components/WatchlistPanel.test.tsx`
- `npm test -- src/components/DetailPanel.test.tsx`
Expected: FAIL for new assertions.

**Step 3: Implement minimal UI sections**

In `WatchlistPanel`:
- add compact "What changed" block from `meta.shadowGate`
In `DetailPanel`:
- optional contextual section when shadow metadata exists

**Step 4: Re-run focused tests**

Run:
- `npm test -- src/components/WatchlistPanel.test.tsx`
- `npm test -- src/components/DetailPanel.test.tsx`
Expected: PASS.

**Step 5: Commit**

```bash
git add src/components/WatchlistPanel.tsx src/components/DetailPanel.tsx src/components/WatchlistPanel.test.tsx src/components/DetailPanel.test.tsx
git commit -m "feat(frontend): add shadow what-changed and leader stability visibility"
```

---

### Task 4: Add provenance/freshness display fields safely (A)

**Files:**
- Modify: `scripts/etl/output_generator.py`
- Modify: `src/lib/types.ts`
- Modify: `src/components/DetailPanel.tsx`
- Test: `scripts/tests/test_output_generator.py`
- Test: `src/components/DetailPanel.test.tsx`

**Step 1: Write failing tests for provenance fields**

Add tests for optional fields:
- `sourceSummary` (or equivalent)
- `signalFreshness` / freshness hint
Ensure backward compatibility when absent.

**Step 2: Run targeted tests to verify failure**

Run:
- `python3 -m pytest scripts/tests/test_output_generator.py -q`
- `npm test -- src/components/DetailPanel.test.tsx`
Expected: FAIL initially.

**Step 3: Implement minimal field generation and rendering**

Generate optional provenance fields in ETL output and show only when present.

**Step 4: Re-run targeted tests**

Run:
- `python3 -m pytest scripts/tests/test_output_generator.py -q`
- `npm test -- src/components/DetailPanel.test.tsx`
Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/etl/output_generator.py src/lib/types.ts src/components/DetailPanel.tsx scripts/tests/test_output_generator.py src/components/DetailPanel.test.tsx
git commit -m "feat(etl): add optional provenance and freshness metadata"
```

---

### Task 5: Baseline-state persistence hardening (C)

**Files:**
- Modify: `scripts/main.py`
- Modify: `scripts/etl/shadow_eval.py`
- Test: `scripts/tests/test_main_compat.py`
- Test: `scripts/tests/test_shadow_eval.py`

**Step 1: Write failing tests for baseline-state persistence**

Add tests that verify:
- stable leader state is persisted consistently in `meta.shadowGate.leaderState`
- WARN/FAIL runs do not overwrite approved-data semantics
- PASS path preserves updated stable state

**Step 2: Run targeted tests to verify failure**

Run:
- `python3 -m pytest scripts/tests/test_main_compat.py -q`
- `python3 -m pytest scripts/tests/test_shadow_eval.py -q`
Expected: at least one FAIL.

**Step 3: Implement minimal persistence normalization**

Normalize leader state serialization/deserialization and keep state keys deterministic.

**Step 4: Re-run targeted tests**

Run:
- `python3 -m pytest scripts/tests/test_main_compat.py -q`
- `python3 -m pytest scripts/tests/test_shadow_eval.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add scripts/main.py scripts/etl/shadow_eval.py scripts/tests/test_main_compat.py scripts/tests/test_shadow_eval.py
git commit -m "refactor(etl): harden shadow leader state persistence semantics"
```

---

### Task 6: ETL complexity reduction by extracting pure helpers (C)

**Files:**
- Modify: `scripts/etl/shadow_eval.py`
- Test: `scripts/tests/test_shadow_eval.py`

**Step 1: Add failing tests for extracted helper behavior (if new helper API exposed)**

Create targeted tests for extracted helpers (leader selection, diff composition, metric packaging).

**Step 2: Refactor internals without behavior change**

Split into clear units:
- metric extraction/computation
- leader policy update
- gate classification/report merge

**Step 3: Run targeted tests**

Run: `python3 -m pytest scripts/tests/test_shadow_eval.py -q`
Expected: PASS.

**Step 4: Commit**

```bash
git add scripts/etl/shadow_eval.py scripts/tests/test_shadow_eval.py
git commit -m "refactor(etl): reduce shadow eval complexity via pure helper extraction"
```

---

### Task 7: Workflow performance hardening with dependency caches (C)

**Files:**
- Modify: `.github/workflows/quarterly-update.yml`
- Test: `scripts/tests/test_workflow_contract.py`

**Step 1: Write failing workflow-contract tests for caching presence**

Add tests asserting workflow contains:
- pip cache step (`~/.cache/pip`)
- npm cache config or equivalent cache step

**Step 2: Run targeted test to verify failure**

Run: `python3 -m pytest scripts/tests/test_workflow_contract.py -q`
Expected: FAIL for cache assertions.

**Step 3: Implement caching steps**

In workflow:
- add pip cache keyed by `scripts/requirements.txt`
- add npm cache keyed by `package-lock.json`
Keep execution semantics unchanged.

**Step 4: Re-run targeted tests**

Run: `python3 -m pytest scripts/tests/test_workflow_contract.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add .github/workflows/quarterly-update.yml scripts/tests/test_workflow_contract.py
git commit -m "perf(ci): add dependency caching for ETL and frontend jobs"
```

---

### Task 8: Docs update for A+C operational model

**Files:**
- Modify: `docs/etl-ops-runbook.md`
- Modify: `docs/etl-architecture.md`
- Modify: `README.md`
- Test: `scripts/tests/test_workflow_contract.py`

**Step 1: Update docs with new operational semantics**

Include:
- leader explainability fields and interpretation
- what-changed panel data meaning
- provenance/freshness field purpose
- workflow cache behavior and expected effect

**Step 2: Run docs-related contract tests**

Run: `python3 -m pytest scripts/tests/test_workflow_contract.py -q`
Expected: PASS.

**Step 3: Commit**

```bash
git add docs/etl-ops-runbook.md docs/etl-architecture.md README.md scripts/tests/test_workflow_contract.py
git commit -m "docs: document A+C operational explainability and workflow performance model"
```

---

### Task 9: Full verification + integration

**Files:**
- Modify: none expected unless fixes required

**Step 1: Run frontend checks**

Run:
- `npm run lint`
- `npm test`
- `npm run build`
Expected: PASS.

**Step 2: Run ETL checks**

Run:
- `python3 -m pytest scripts/tests -q`
Expected: PASS.

**Step 3: Local shadow smoke**

Run:
- `python3 scripts/main.py --shadow-only --shadow-baseline artifacts/baseline.json --shadow-current src/data/data.ai.json --shadow-output artifacts/shadow_eval.json`
Expected: valid report with explainability fields.

**Step 4: Commit final integration fixes if needed**

```bash
git add -A
git commit -m "chore: finalize A+C radar ops hardening"
```

---

## Constraints

- Keep strict quality thresholds and 3-run leader inertia.
- No threshold relaxation as workaround.
- Preserve backward compatibility in `src/data/data.ai.json` (new fields optional).
- Do not change Synthetic base URL behavior.

## Final Validation Gate

Must pass before merge/push:
- `npm run lint`
- `npm test`
- `npm run build`
- `python3 -m pytest scripts/tests -q`

## Rollback Plan

1. Revert workflow cache + shadow explainability commits if regressions occur.
2. Keep frontend visualization changes only if they are metadata-optional and all tests pass.
3. Restore previous report shape while preserving strict gate decision logic.
