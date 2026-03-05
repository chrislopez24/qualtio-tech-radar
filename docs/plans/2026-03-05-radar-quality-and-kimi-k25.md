# Radar Quality + Synthetic Kimi K2.5 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Improve the Tech Radar UX/content quality end-to-end, add decision-grade metadata, and run a controlled ETL model evaluation with `hf:moonshotai/Kimi-K2.5` while keeping the current Synthetic base URL behavior unchanged.

**Architecture:** We will deliver in vertical slices: (1) filtering and UI usability, (2) richer data schema and detail rendering, (3) ETL configuration and model evaluation workflow, and (4) verification + docs. Frontend stays in Next.js/React with local JSON-backed rendering; ETL stays OpenAI-compatible via existing `SYNTHETIC_API_URL` path and only switches model through config/env.

**Tech Stack:** Next.js 16, React 19, TypeScript, Vitest, Python ETL, Pytest, Synthetic OpenAI-compatible API.

---

### Task 1: Baseline verification + branch safety

**Files:**
- Modify: none
- Test: N/A

**Step 1: Verify current git status**

Run: `git status`
Expected: clean or known pending changes listed.

**Step 2: Run frontend baseline tests**

Run: `npm test`
Expected: PASS for existing test suite.

**Step 3: Run ETL baseline tests**

Run: `python3 -m pytest scripts/tests -q`
Expected: PASS for existing ETL tests.

**Step 4: Capture baseline notes**

Record current behavior:
- Search-only filtering (name/description/ring/quadrant)
- Existing detail fields
- Existing model default in config (`hf:MiniMaxAI/MiniMax-M2.5`)

**Step 5: Commit (optional checkpoint)**

```bash
git add -A
git commit -m "chore: capture baseline before radar quality improvements"
```

---

### Task 2: Add structured filter controls (ring/quadrant/trend/confidence)

**Files:**
- Create: `src/lib/radar-filters.ts`
- Modify: `src/lib/types.ts`
- Modify: `src/app/page.tsx`
- Modify: `src/components/RadarSidebar.tsx`
- Test: `src/lib/radar-filters.test.ts`

**Step 1: Write failing tests for filter combinator logic**

Create tests covering:
- no filters => all visible
- ring + quadrant intersection
- trend filtering
- confidence min threshold
- search + structured filters combined

**Step 2: Run test to verify it fails**

Run: `npm test -- src/lib/radar-filters.test.ts`
Expected: FAIL because helper does not exist yet.

**Step 3: Implement minimal filter helper**

In `src/lib/radar-filters.ts`:
- Add `RadarFilterState` type.
- Add `filterTechnologies(technologies, searchQuery, filters)`.
- Reuse `matchesTechnologySearch` to preserve current behavior.

**Step 4: Update page state and data flow**

In `src/app/page.tsx`:
- Add controlled filter state.
- Replace direct `matchesTechnologySearch` usage with `filterTechnologies`.
- Pass filter state/setters to sidebar.

**Step 5: Add compact controls to sidebar**

In `src/components/RadarSidebar.tsx`:
- Add ring and quadrant chips/toggles.
- Add trend selector and confidence slider/input.
- Keep visible/filtered counters synced with final filtered list.

**Step 6: Run focused tests**

Run: `npm test -- src/lib/radar-filters.test.ts`
Expected: PASS.

**Step 7: Run full frontend tests**

Run: `npm test`
Expected: PASS.

**Step 8: Commit**

```bash
git add src/lib/radar-filters.ts src/lib/radar-filters.test.ts src/lib/types.ts src/app/page.tsx src/components/RadarSidebar.tsx
git commit -m "feat: add composable radar filters for ring quadrant trend and confidence"
```

---

### Task 3: Enrich radar item schema with decision metadata

**Files:**
- Modify: `src/lib/types.ts`
- Modify: `src/data/data.ai.json`
- Modify: `src/data/data.ai.history.json` (only if required for compatibility)
- Test: `src/lib/radar-data-schema.test.ts`

**Step 1: Write failing schema compatibility tests**

Add tests that validate:
- New optional fields are accepted.
- Existing items without new fields still parse.
- Decision metadata shape is stable.

**Step 2: Run tests to verify failure**

Run: `npm test -- src/lib/radar-data-schema.test.ts`
Expected: FAIL before types/schema updates.

**Step 3: Add optional metadata fields to `AITechnology`**

In `src/lib/types.ts`, add optional fields:
- `whyNow?: string`
- `useCases?: string[]`
- `avoidWhen?: string[]`
- `maturityLevel?: 'poc' | 'pilot' | 'production'`
- `adoptionEffort?: 's' | 'm' | 'l'`
- `risk?: { security?: string; lockIn?: string; talent?: string; cost?: string }`
- `owner?: string`
- `nextStep?: string`
- `nextReviewAt?: string`
- `evidence?: string[]`
- `alternatives?: string[]`

**Step 4: Add sample metadata to a small subset in `data.ai.json`**

Update 3-5 representative technologies to include new fields.

**Step 5: Run schema tests**

Run: `npm test -- src/lib/radar-data-schema.test.ts`
Expected: PASS.

**Step 6: Run full frontend tests**

Run: `npm test`
Expected: PASS.

**Step 7: Commit**

```bash
git add src/lib/types.ts src/data/data.ai.json src/lib/radar-data-schema.test.ts
git commit -m "feat: extend radar item schema with decision metadata"
```

---

### Task 4: Upgrade detail panel with actionable sections

**Files:**
- Modify: `src/components/DetailPanel.tsx`
- Test: `src/components/DetailPanel.test.tsx`

**Step 1: Write failing UI tests**

Cover rendering for:
- `whyNow`
- `useCases`
- `avoidWhen`
- risk block
- owner + next review + next step
- fallback when fields missing

**Step 2: Run tests to verify failure**

Run: `npm test -- src/components/DetailPanel.test.tsx`
Expected: FAIL before component updates.

**Step 3: Implement detail sections**

Update `DetailPanel.tsx` to render sections conditionally:
- “Why now”
- “Use cases”
- “Avoid when”
- “Risks”
- “Owner & review”
- “Next step”
- “Evidence / alternatives”

**Step 4: Ensure no layout break on small screens**

Manual check in browser:
- open one item with full metadata
- open one item with legacy fields only

**Step 5: Run tests**

Run:
- `npm test -- src/components/DetailPanel.test.tsx`
- `npm test`

Expected: PASS.

**Step 6: Commit**

```bash
git add src/components/DetailPanel.tsx src/components/DetailPanel.test.tsx
git commit -m "feat: add actionable decision sections to technology detail panel"
```

---

### Task 5: Make Watchlist operationally actionable

**Files:**
- Modify: `src/components/WatchlistPanel.tsx`
- Modify: `src/lib/types.ts` (if watchlist metadata shape differs)
- Test: `src/components/WatchlistPanel.test.tsx`

**Step 1: Write failing tests for watchlist actions**

Validate watchlist item shows:
- owner (if present)
- next step summary
- review date badge/status

**Step 2: Run tests to verify failure**

Run: `npm test -- src/components/WatchlistPanel.test.tsx`
Expected: FAIL.

**Step 3: Implement watchlist action fields and display**

In `WatchlistPanel.tsx`:
- add compact “action” line
- add review recency indicator (upcoming/overdue)
- preserve click-to-open detail behavior

**Step 4: Run tests**

Run:
- `npm test -- src/components/WatchlistPanel.test.tsx`
- `npm test`

Expected: PASS.

**Step 5: Commit**

```bash
git add src/components/WatchlistPanel.tsx src/components/WatchlistPanel.test.tsx src/lib/types.ts
git commit -m "feat: make watchlist entries actionable with owner next step and review status"
```

---

### Task 6: Configure Kimi K2.5 support without changing current base URL behavior

**Files:**
- Modify: `scripts/config.yaml`
- Modify: `scripts/etl/classifier.py`
- Modify: `scripts/etl/ai_filter.py`
- Modify: `README.md`
- Test: `scripts/tests/test_config_schema.py`
- Test: `scripts/tests/test_classifier.py`
- Test: `scripts/tests/test_ai_filter.py`

**Step 1: Write failing tests for model configurability**

Add/adjust tests to assert:
- model id can be set to `hf:moonshotai/Kimi-K2.5`
- default base URL fallback remains existing current value (`https://api.synthetic.new/v1`)

**Step 2: Run focused ETL tests to verify failure**

Run:
- `python3 -m pytest scripts/tests/test_config_schema.py -q`
- `python3 -m pytest scripts/tests/test_classifier.py -q`
- `python3 -m pytest scripts/tests/test_ai_filter.py -q`

Expected: at least one FAIL before config/test updates.

**Step 3: Update model config default**

In `scripts/config.yaml` set:
- `classification.model: hf:moonshotai/Kimi-K2.5`

**Step 4: Preserve base URL behavior explicitly**

In classifier/filter code:
- keep existing default fallback URL exactly as-is
- add comments/doc clarity that URL is intentionally unchanged

**Step 5: Update README run examples**

Document:
- `SYNTHETIC_MODEL=hf:moonshotai/Kimi-K2.5`
- explicitly note: do not change `SYNTHETIC_API_URL` if current setup already works

**Step 6: Run ETL tests**

Run:
- `python3 -m pytest scripts/tests/test_config_schema.py -q`
- `python3 -m pytest scripts/tests/test_classifier.py -q`
- `python3 -m pytest scripts/tests/test_ai_filter.py -q`

Expected: PASS.

**Step 7: Commit**

```bash
git add scripts/config.yaml scripts/etl/classifier.py scripts/etl/ai_filter.py README.md scripts/tests/test_config_schema.py scripts/tests/test_classifier.py scripts/tests/test_ai_filter.py
git commit -m "feat: add kimi k2.5 model configuration while preserving synthetic base url behavior"
```

---

### Task 7: Run ETL A/B comparison (MiniMax vs Kimi)

**Files:**
- Create: `artifacts/model-evals/2026-03-05-kimi-k25-vs-minimax.md`
- Modify: none required (runtime only)
- Test: runtime validation commands

**Step 1: Run ETL with current baseline model (MiniMax)**

Run:
- `SYNTHETIC_MODEL=hf:MiniMaxAI/MiniMax-M2.5 python3 scripts/main.py`

Capture:
- total output count
- ring distribution
- avg confidence
- ETL runtime

**Step 2: Run ETL with Kimi K2.5**

Run:
- `SYNTHETIC_MODEL=hf:moonshotai/Kimi-K2.5 python3 scripts/main.py`

Capture same metrics.

**Step 3: Compare quality and cost proxies**

Create comparison table with:
- overlap rate
- major ring shifts
- description quality spot-check (5 items)
- token/call metrics from logs

**Step 4: Save report**

Write findings to:
- `artifacts/model-evals/2026-03-05-kimi-k25-vs-minimax.md`

**Step 5: Commit**

```bash
git add artifacts/model-evals/2026-03-05-kimi-k25-vs-minimax.md
git commit -m "docs: add minimax vs kimi k2.5 etl evaluation report"
```

---

### Task 8: Final verification and release prep

**Files:**
- Modify: `docs/etl-ops-runbook.md` (if workflow changes)
- Test: full test matrix

**Step 1: Run frontend verification**

Run:
- `npm run lint`
- `npm test`
- `npm run build`

Expected: PASS.

**Step 2: Run ETL verification**

Run:
- `python3 -m pytest scripts/tests -q`

Expected: PASS.

**Step 3: Smoke-test app behavior manually**

Check:
- search + structured filters
- detail panel sections render correctly
- watchlist actionable info visible

**Step 4: Update runbook if needed**

Document the model switch and A/B procedure in `docs/etl-ops-runbook.md`.

**Step 5: Final commit**

```bash
git add docs/etl-ops-runbook.md
git commit -m "docs: update radar ops runbook for kimi k2.5 model workflow"
```

---

## Notes / Constraints

- **Hard constraint from stakeholder:** keep current Synthetic base URL behavior unchanged; do not force migration.
- Model evaluation must be done by changing `SYNTHETIC_MODEL` and/or `classification.model`, not by base URL replacement.
- Preserve backward compatibility for existing `src/data/data.ai.json` entries.
- Favor optional schema fields to avoid breaking old snapshots.

## Test Matrix (must pass before merge)

### Frontend
- `npm run lint`
- `npm test`
- `npm run build`

### ETL
- `python3 -m pytest scripts/tests -q`
- ETL smoke run with:
  - `SYNTHETIC_MODEL=hf:MiniMaxAI/MiniMax-M2.5`
  - `SYNTHETIC_MODEL=hf:moonshotai/Kimi-K2.5`

---

## Rollback plan

If Kimi quality is worse than baseline:
1. Revert `classification.model` in `scripts/config.yaml` to `hf:MiniMaxAI/MiniMax-M2.5`.
2. Keep UI/schema improvements.
3. Retain A/B report and mark Kimi as watchlist candidate.
