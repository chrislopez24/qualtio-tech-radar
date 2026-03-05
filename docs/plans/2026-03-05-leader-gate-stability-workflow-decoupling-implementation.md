# Leader Gate Stability + Workflow Decoupling Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Enforce strict leader quality with 3-run temporal inertia, decouple ETL gate outcomes from frontend deployability on GitHub Pages, and execute a two-phase code cleanup (ETL/workflow first, frontend second) without regressions.

**Architecture:** We will introduce a persistent shadow-gate state model that tracks stable leaders and candidate leader transitions across runs, then evaluate gate outcomes as pass/warn/fail using strict thresholds plus promotion rules. Workflow jobs will be split so ETL candidate validation and frontend deployment are independent, with production data updates gated by PASS only. Cleanup tasks refactor shadow-eval internals and frontend rendering utilities while preserving behavior.

**Tech Stack:** Python ETL + Pytest, GitHub Actions YAML, Next.js/React/TypeScript + Vitest.

---

### Task 1: Add leader-inertia state model and tests (TDD)

**Files:**
- Modify: `scripts/etl/shadow_eval.py`
- Test: `scripts/tests/test_shadow_eval.py`

**Step 1: Write failing unit tests for candidate tracking**

Add tests for:
- first observed leader change creates candidate with `consecutive_count=1`
- repeated same change increments count
- interruption resets candidate count
- promotion occurs at exactly 3 consecutive runs

**Step 2: Run targeted tests to confirm failure**

Run: `python3 -m pytest scripts/tests/test_shadow_eval.py -q`
Expected: FAIL for newly added scenarios.

**Step 3: Implement minimal state data structures**

In `scripts/etl/shadow_eval.py`, add helpers for:
- loading previous gate state from baseline payload/report
- tracking `stable_leaders`
- tracking `candidate_changes` keyed by `leader_id + change_type`

**Step 4: Implement update logic for consecutive runs**

Implement pure functions that:
- compute observed-vs-stable diffs
- update candidate counters
- reset non-repeated candidates
- promote candidates at threshold 3

**Step 5: Re-run targeted tests**

Run: `python3 -m pytest scripts/tests/test_shadow_eval.py -q`
Expected: PASS for added leader-inertia tests.

**Step 6: Commit checkpoint**

```bash
git add scripts/etl/shadow_eval.py scripts/tests/test_shadow_eval.py
git commit -m "feat(etl): add 3-run leader inertia state tracking"
```

---

### Task 2: Add pass/warn/fail gate classification and richer report output

**Files:**
- Modify: `scripts/etl/shadow_eval.py`
- Test: `scripts/tests/test_shadow_eval.py`

**Step 1: Write failing tests for gate status mapping**

Add tests to assert:
- PASS when thresholds met and no blocking instability
- WARN when leader candidate drift exists with count < 3
- FAIL on hard threshold breaches

**Step 2: Run targeted tests to confirm failure**

Run: `python3 -m pytest scripts/tests/test_shadow_eval.py -q`
Expected: FAIL for new gate status tests.

**Step 3: Implement gate classification function**

Add logic that evaluates:
- strict metric thresholds (including `leader_coverage`)
- candidate state context
- resulting `gate_status` and `next_action`

**Step 4: Extend report schema**

Populate in output report:
- `gate_status`
- `leader_transition_summary`
- `candidate_changes`
- `stable_leaders`
- `next_action`

**Step 5: Re-run targeted tests**

Run: `python3 -m pytest scripts/tests/test_shadow_eval.py -q`
Expected: PASS.

**Step 6: Commit checkpoint**

```bash
git add scripts/etl/shadow_eval.py scripts/tests/test_shadow_eval.py
git commit -m "feat(etl): classify shadow gate as pass warn fail with transition details"
```

---

### Task 3: Use last approved stable baseline for comparison

**Files:**
- Modify: `scripts/main.py`
- Modify: `scripts/etl/shadow_eval.py`
- Test: `scripts/tests/test_main_compat.py`
- Test: `scripts/tests/test_shadow_eval.py`

**Step 1: Write failing tests for baseline selection policy**

Add tests for:
- using explicit `--shadow-baseline` when provided
- falling back to last approved stable baseline metadata when available
- not replacing stable baseline on WARN/FAIL candidate runs

**Step 2: Run targeted tests to confirm failure**

Run:
- `python3 -m pytest scripts/tests/test_main_compat.py -q`
- `python3 -m pytest scripts/tests/test_shadow_eval.py -q`
Expected: at least one FAIL.

**Step 3: Implement baseline source selection behavior**

Update CLI orchestration (`scripts/main.py`) and evaluation helpers to:
- detect approved baseline state
- evaluate candidate run against approved baseline
- preserve approved baseline pointer unless PASS criteria is met

**Step 4: Re-run targeted tests**

Run:
- `python3 -m pytest scripts/tests/test_main_compat.py -q`
- `python3 -m pytest scripts/tests/test_shadow_eval.py -q`
Expected: PASS.

**Step 5: Commit checkpoint**

```bash
git add scripts/main.py scripts/etl/shadow_eval.py scripts/tests/test_main_compat.py scripts/tests/test_shadow_eval.py
git commit -m "feat(etl): compare shadow runs against last approved stable baseline"
```

---

### Task 4: Decouple workflow jobs (ETL gate vs frontend deploy)

**Files:**
- Modify: `.github/workflows/quarterly-update.yml`
- Test: `scripts/tests/test_workflow_contract.py`

**Step 1: Write failing workflow-contract tests**

Add/adjust tests asserting:
- frontend build/deploy path is not hard-blocked by ETL gate failure
- data commit/update step requires gate PASS for candidate data overwrite
- workflow still uploads shadow artifacts on failures

**Step 2: Run targeted tests to confirm failure**

Run: `python3 -m pytest scripts/tests/test_workflow_contract.py -q`
Expected: FAIL before YAML updates.

**Step 3: Refactor workflow into explicit responsibilities**

In `.github/workflows/quarterly-update.yml`:
- keep ETL candidate run + shadow eval in one job
- ensure artifact upload uses `if: always()`
- gate data overwrite/push of new ETL output by PASS condition
- keep frontend build/deploy able to run for frontend-only changes using validated repository data

**Step 4: Re-run workflow contract tests**

Run: `python3 -m pytest scripts/tests/test_workflow_contract.py -q`
Expected: PASS.

**Step 5: Commit checkpoint**

```bash
git add .github/workflows/quarterly-update.yml scripts/tests/test_workflow_contract.py
git commit -m "feat(ci): decouple frontend deploy from ETL shadow gate outcome"
```

---

### Task 5: ETL/workflow cleanup pass (maintainability, no behavior drift)

**Files:**
- Modify: `scripts/etl/shadow_eval.py`
- Modify: `scripts/main.py`
- Modify: `scripts/tests/test_shadow_eval.py`
- Modify: `scripts/tests/test_main_compat.py`

**Step 1: Add failing tests for extracted helper behavior (if needed)**

Add focused tests for any new helper functions extracted during cleanup.

**Step 2: Refactor for clarity**

Apply cleanup:
- isolate metric computation from policy evaluation
- isolate transition-state update from report rendering
- reduce duplication in diff/summary formatting
- normalize type hints and constant declarations

**Step 3: Run focused ETL tests**

Run:
- `python3 -m pytest scripts/tests/test_shadow_eval.py -q`
- `python3 -m pytest scripts/tests/test_main_compat.py -q`
Expected: PASS.

**Step 4: Commit checkpoint**

```bash
git add scripts/etl/shadow_eval.py scripts/main.py scripts/tests/test_shadow_eval.py scripts/tests/test_main_compat.py
git commit -m "refactor(etl): simplify shadow evaluation policy and reporting internals"
```

---

### Task 6: Frontend cleanup pass (Detail/Watchlist maintainability)

**Files:**
- Modify: `src/components/DetailPanel.tsx`
- Modify: `src/components/WatchlistPanel.tsx`
- Modify: `src/components/DetailPanel.test.tsx`
- Modify: `src/components/WatchlistPanel.test.tsx`

**Step 1: Add/adjust failing UI tests for cleanup-protected behavior**

Cover:
- unchanged rendering for decision metadata blocks
- review badge status labels/tone mapping
- fallback behavior for missing optional fields

**Step 2: Run focused tests to confirm baseline expectations**

Run:
- `npm test -- src/components/DetailPanel.test.tsx`
- `npm test -- src/components/WatchlistPanel.test.tsx`
Expected: PASS or FAIL only for intended test updates.

**Step 3: Refactor UI code without behavior changes**

Cleanups:
- extract small render helpers to reduce repeated JSX branches
- centralize label formatting for review/owner/action lines
- simplify conditional blocks and improve readability

**Step 4: Re-run focused tests**

Run:
- `npm test -- src/components/DetailPanel.test.tsx`
- `npm test -- src/components/WatchlistPanel.test.tsx`
Expected: PASS.

**Step 5: Commit checkpoint**

```bash
git add src/components/DetailPanel.tsx src/components/WatchlistPanel.tsx src/components/DetailPanel.test.tsx src/components/WatchlistPanel.test.tsx
git commit -m "refactor(frontend): clean detail and watchlist rendering paths"
```

---

### Task 7: Documentation updates for new gate policy and workflow behavior

**Files:**
- Modify: `docs/etl-ops-runbook.md`
- Modify: `docs/etl-architecture.md`
- Modify: `README.md`
- Test: `scripts/tests/test_workflow_contract.py`

**Step 1: Update docs with policy and operational behavior**

Document:
- strict thresholds + 3-run leader inertia
- pass/warn/fail definitions
- stable baseline source policy
- workflow decoupling behavior (frontend deployability with last validated data)

**Step 2: Run docs contract tests**

Run: `python3 -m pytest scripts/tests/test_workflow_contract.py -q`
Expected: PASS.

**Step 3: Commit checkpoint**

```bash
git add docs/etl-ops-runbook.md docs/etl-architecture.md README.md scripts/tests/test_workflow_contract.py
git commit -m "docs: document leader inertia policy and deploy decoupling behavior"
```

---

### Task 8: Full verification matrix and release readiness

**Files:**
- Modify: none expected (unless fixes are required)

**Step 1: Run frontend lint/test/build**

Run:
- `npm run lint`
- `npm test`
- `npm run build`
Expected: PASS.

**Step 2: Run full ETL test suite**

Run:
- `python3 -m pytest scripts/tests -q`
Expected: PASS.

**Step 3: Run local shadow-eval smoke with explicit baseline/current**

Run:
- `python3 scripts/main.py --shadow-only --shadow-baseline artifacts/baseline.json --shadow-current src/data/data.ai.json --shadow-output artifacts/shadow_eval.json`
Expected: report generated with `gate_status` and transition fields.

**Step 4: Optional workflow dispatch validation**

Run (if desired):
- `gh workflow run "Quarterly Tech Radar Update"`
- monitor run until completion and verify decoupled behavior in jobs.

**Step 5: Final integration commit (if any post-verification fixes)**

```bash
git add -A
git commit -m "chore: finalize leader stability gate and workflow decoupling"
```

---

## Notes / Constraints

- Keep `leader_coverage` strict (no relaxed default threshold).
- Promote leader set changes only after 3 consecutive supporting runs.
- Do not overwrite validated production data on WARN/FAIL.
- Frontend deploy path must remain usable for frontend-only iterations.
- Preserve existing Synthetic base URL behavior.

## Test Matrix (must pass)

### Frontend
- `npm run lint`
- `npm test`
- `npm run build`

### ETL
- `python3 -m pytest scripts/tests -q`
- targeted: `python3 -m pytest scripts/tests/test_shadow_eval.py -q`
- targeted: `python3 -m pytest scripts/tests/test_workflow_contract.py -q`

## Rollback Plan

1. Revert workflow YAML + shadow eval policy commits.
2. Keep frontend cleanup commits if independent and passing.
3. Restore previous baseline comparison behavior while preserving artifact logs for diagnosis.
